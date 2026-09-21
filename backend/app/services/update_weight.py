from typing import Any, Dict, Optional

import logging
import pandas as pd

from pandas import DataFrame
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)

WEIGHT_LEARNING_RATE = 0.1 # 가중치 학습률
MIN_PRESENTATIONS = 10 # 가중치 업데이트에 필요한 최소 발표 수

ORDER_COLUMN = "created_at"

FEATURES = [
    "spm_mean",
    "pitch_variation_mean",
    "db_mean",
    "silence_mean",
    "filler_reversed_mean"
]

TARGET = "attention_mean"
VOICE_SATISFACTION = "voice_satisfaction"
PREDICTION = "predicted_attention"

# 초기 가중치
# DB에 저장 후 가져와서 사용하도록 수정 필요
DEFAULT_WEIGHT: Dict[str, float] = {
    "spm_penalty_weight" : 0.5,
    "pitch_weight": 0.5,
    "db_boost_weight" : 0.5,
    "silence_penalty_weight" : 0.5,
    "filler_penalty_weight" : 0.5
}

FEATURE_WEIGHT_KEY = {
    "spm_mean": "spm_penalty_weight",
    "pitch_variation_mean": "pitch_weight",
    "db_mean": "db_boost_weight",
    "silence_mean": "silence_penalty_weight",
    "filler_reversed_mean": "filler_penalty_weight"
}

# 청중의 설문 데이터를 기반으로 각 속성들과의 스피어만 상관계수 계산
def calculate_spearmanr(result: DataFrame, column_x: str, column_y: str) -> Dict[str, Any]:
    
    data = result[[column_x, column_y]].dropna()
    
    sample_length = len(data)
    
    if sample_length < 2:
        return {
            "correlation": None,
            "p_value": None,
            "sample_size": sample_length,
            "updated": False,
            "reason": "유효한 데이터가 부족합니다."
        }
    
    # feature 값이 모두 동일한 경우
    if data[column_x].nunique() <= 1:
        return {
            "correlation": 0.0,
            "p_value": 1.0,
            "sample_size": sample_length,
            "updated": False,
            "reason": f"'{column_x}' 값의 변화가 없습니다.",
        }
        
    # 집중도 값이 모두 동일한 경우
    if data[column_y].nunique() <= 1:
        return {
            "correlation": 0.0,
            "p_value": 1.0,
            "sample_size": sample_length,
            "updated": False,
            "reason": f"'{column_y}' 값의 변화가 없습니다.",
        }
        
    correlation, p_value = spearmanr(data[column_x], data[column_y])
    
    if pd.isna(correlation):
        correlation = 0.0
        
    if pd.isna(p_value):
        p_value = 1.0
    
    return {
        "correlation": correlation,
        "p_value": p_value,
        "sample_size": sample_length,
        "updated": True,
    }

def feature_corr(result: DataFrame)-> Dict[str, Dict[str, Any]]:
    correlations = {}
    
    for feature in FEATURES:
        correlations[feature] = (calculate_spearmanr(result, feature, TARGET))
        
    return correlations

def correlation_to_target_weights(correlations: Dict[str, Dict[str, Any]]) -> Dict[str, float]:

    target_weights = {}

    for feature in FEATURES:
        base = DEFAULT_WEIGHT[FEATURE_WEIGHT_KEY[feature]]
        correlation_data = correlations.get(feature, {})
        rho = correlation_data.get("correlation")
        p_value = correlation_data.get("p_value")
        
        if rho is None or p_value is None or p_value >= 0.05:
            continue
        
        target_weights[feature] = max(0.0, min(1.0, base + 0.5 * float(rho)))

    return target_weights

def update_weights(old_weights: Dict[str, float], target_weights: Dict[str, float]) -> Dict[str, float]:
    updated_weights = old_weights.copy()
    
    for feature, weight_key in FEATURE_WEIGHT_KEY.items():
        
        old_weight = old_weights.get(weight_key, DEFAULT_WEIGHT[weight_key])
        target_weight = target_weights.get(feature, old_weight)

        new_weight = old_weight + WEIGHT_LEARNING_RATE * (target_weight - old_weight)

        updated_weights[weight_key] = max(0.0, min(1.0, new_weight))
        
    return updated_weights        

# DB에 last_trained_presentation_count를 추가하여 마지막 가중치 업데이트 인덱스를 저장 -> 마지막 가중치 업데이트 이후 다음 업데이트 시점에서 업데이트를 하도록함
def update_group_model(
    presentation_data: DataFrame,
    audience_group: str,
    old_weights: Optional[Dict[str, float]],
    last_trained_count: int = 0
) -> Dict[str, Any]:
    
    group_data = presentation_data[presentation_data["audience_group"] == audience_group].copy()
    
    if "learning_data_available" in group_data.columns:
        group_data = group_data[group_data["learning_data_available"].fillna(False).astype(bool)]
    
    if ORDER_COLUMN in group_data.columns:
        group_data = group_data.sort_values(ORDER_COLUMN)
    else:
        logger.warning("'%s' 컬럼이 없어 입력된 순서를 발표 순서로 사용합니다.", ORDER_COLUMN)
 
    presentation_count = len(group_data)
    new_count = presentation_count - last_trained_count
 
    if new_count < MIN_PRESENTATIONS:
        return {
            "updated": False,
            "audience_group": audience_group,
            "presentation_count": presentation_count,
            "reason": f"{audience_group} 그룹의 새 발표 데이터가 {MIN_PRESENTATIONS}개 미만입니다.",
        }
        
    # 아직 학습하지 않은 발표 중 가장 오래된 10개를 한 배치로 사용
    batch_data = group_data.iloc[last_trained_count:last_trained_count + MIN_PRESENTATIONS].copy()

    if len(batch_data) < MIN_PRESENTATIONS:
        return {
            "updated": False,
            "audience_group": audience_group,
            "presentation_count": presentation_count,
            "reason": "완성된 발표 배치가 없습니다."
        }
        
    if old_weights is None:
        old_weights = DEFAULT_WEIGHT.copy()
        
    correlations = feature_corr(batch_data)
    target_weights = correlation_to_target_weights(correlations)
    updated_weights = update_weights(old_weights, target_weights)
        
    return {
        "updated": True,
        "audience_group": audience_group,
        "presentation_count": presentation_count,
        "batch_size": len(batch_data),
        "trained_presentation_count": last_trained_count + len(batch_data),
        "correlations": correlations,

        "old_weights": old_weights,
        "target_weights": target_weights,
        "updated_weights": updated_weights
    }