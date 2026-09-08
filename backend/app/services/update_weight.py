from typing import Any, Dict

import pandas as pd
from pandas import DataFrame
from scipy.stats import spearmanr

LEARNING_RATE = 0.1 # 학습률 지정

MIN_PRESENTATIONS = 10 # 가중치 업데이트에 필요한 최소 발표 수

FEATURES = [
    "spm_mean",
    "pitch_mean",
    "db_mean",
    "silence_mean",
    "filler_mean",
    "monotony_mean"
]

TARGET = "attention_mean"

# 초기 가중치
# DB에 저장 후 가져와서 사용하도록 수정 필요
DEFAULT_WEIGHT: Dict[str, float] = {
    "spm_penalty_weight" : 0.5,
    "pitch_penalty_weight" : 0.5,
    "db_boost_weight" : 0.5,
    "silence_penalty_weight" : 0.5,
    "filler_penalty_weight" : 0.5,
    "monotone_penalty_weight" : 0.5
}

DEFAULT_THRESHOLD: Dict[str, float] = {
    "fast_spm_threshold": 350.0,
    "slow_spm_threshold": 250.0,
    "silence_penalty_threshold": 5.0,
    "filler_60sec_limit": 5.0,
    "monotone_penalty_threshold": 0.08,
    "excessive_pitch_threshold": 0.25
}

FEATURE_WEIGHT_KEY = {
    "spm_mean": "spm_penalty_weight",
    "pitch_mean": "pitch_penalty_weight",
    "db_mean": "db_boost_weight",
    "silence_mean": "silence_penalty_weight",
    "filler_mean": "filler_penalty_weight",
    "monotony_mean": "monotone_penalty_weight"
}

# Feature별 모델 적용 방향
FEATURE_DIRECTION = {
    "spm_mean": -1,
    "pitch_mean": -1,
    "db_mean": +1,
    "silence_mean": -1,
    "filler_mean": -1,
    "monotony_mean": -1
}

# 청중의 설문 데이터를 기반으로 각 속성들과의 스피어만 상관계수 계산
def calculate_spearmanr(result: DataFrame, feature: str) -> Dict[str, Any]:
    
    data = result[[feature, TARGET]].dropna()
    
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
    if data[feature].nunique() <= 1:
        return {
            "correlation": 0.0,
            "p_value": 1.0,
            "sample_size": sample_length,
            "updated": False,
            "reason": f"'{feature}' 값의 변화가 없습니다.",
        }
        
    # 집중도 값이 모두 동일한 경우
    if data[TARGET].nunique() <= 1:
        return {
            "correlation": 0.0,
            "p_value": 1.0,
            "sample_size": sample_length,
            "updated": False,
            "reason": "집중도 값의 변화가 없습니다.",
        }
        
    correlation, p_value = spearmanr(data[feature], data[TARGET])
    
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
        correlations[feature] = (calculate_spearmanr(result, feature))
        
    return correlations

# default_weight는 데이터 베이스에 저장 후 가져옴
def correlation_to_weights(correlations: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    target_weights: Dict[str, float] = {}
    
    for feature in FEATURES:
        correlation_data = correlations.get(feature, {})
        rho = correlation_data.get("correlation") 
        
        if rho is None:
            target_weights[feature] = 0.0
            continue
        
        target_weights[feature] = abs(float(rho))
  
    return target_weights

def make_directional_target_weights(correlations: Dict[str, Dict[str, Any]]) -> Dict[str, float]:

    target_weights = {}

    for feature in FEATURES:
        correlation_data = correlations.get(feature, {})
        rho = correlation_data.get("correlation")

        if rho is None:
            target_weights[feature] = 0.0
            continue

        rho = float(rho)
        model_direction = FEATURE_DIRECTION[feature]

        if rho > 0:
            data_direction = 1
        elif rho < 0:
            data_direction = -1
        else:
            data_direction = 0

        if data_direction == model_direction:
            target_weight = abs(rho)

        elif data_direction != 0:
            target_weight = abs(rho) * 0.5

        else:
            target_weight = 0.0

        target_weights[feature] = target_weight

    return target_weights

def update_weights(old_weights: Dict[str, float], target_weights: Dict[str, float]) -> Dict[str, float]:
    updated_weights = {}
    
    for feature in FEATURES:
        
        weight_key = FEATURE_WEIGHT_KEY[feature]
        
        old_weight = old_weights.get(weight_key, DEFAULT_WEIGHT[weight_key])
        target_weight = target_weights.get(feature, old_weight)
        
        new_weight = (old_weight + LEARNING_RATE * (target_weight - old_weight))
        updated_weights[weight_key] = max(0.0, new_weight)
    
    return updated_weights        

def analyze_feature_direction(correlations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result = {}
    
    for feature in FEATURES:
        correlation_data = correlations.get(feature, {})
        rho = correlation_data.get("correlation")
        
        model_direction = FEATURE_DIRECTION[feature]
        
        if rho is None:
            result[feature] = {
                "rho": None,
                "model_direction": model_direction,
                "data_direction": 0,
                "direction_match": None
            }
            
            continue
        
        rho = float(rho)
        
        if rho > 0:
            data_direction = 1
        elif rho < 0:
            data_direction = -1
        else:
            data_direction = 0
        
        if data_direction == 0:
            direction_match = None
        else:
            direction_match = (data_direction == model_direction)
            
        result[feature] = {
            "rho": rho,
            "model_direction": model_direction,
            "data_direction": data_direction,
            "direction_match": direction_match
        }
        
    return result

'''
def update_threshold(df: DataFrame, corr: Dict[str, Any]):
    actual_attention = df['attention']
    error = predicted_attention - actual_attention
    delta = learning_rate * error * abs(corr)
    new_threshold = old_threshold + direction * delta 
'''

# DB에 last_trained_presentation_count를 추가하여 마지막 가중치 업데이트 인덱스를 저장 -> 마지막 가중치 업데이트 이후 다음 업데이트 시점에서 업데이트를 하도록함
def update_group_model(
    presentation_data: DataFrame,
    audience_group: str,
    old_weights: Dict[str, float] | None = None,
    current_thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    group_data = presentation_data[presentation_data["audience_group"]== audience_group].copy()
    
    # 발표 ID 기준으로 오래된 발표부터 정렬
    if "presentation_id" in group_data.columns:
        group_data = group_data.sort_values("presentation_id")
        
    presentation_count = len(group_data)
    
    if presentation_count < MIN_PRESENTATIONS:
        return {
            "updated": False,
            "audience_group": audience_group,
            "presentation_count": presentation_count,
            "reason": (f"{audience_group} 그룹의 발표 데이터가 {MIN_PRESENTATIONS}개 미만입니다.")
        }
        
    batch_count = presentation_count // MIN_PRESENTATIONS
    batch_index = batch_count - 1
    
    start_index = (batch_index * MIN_PRESENTATIONS)
    end_index = (start_index + MIN_PRESENTATIONS)
    
    batch_data = group_data.iloc[start_index:end_index].copy()
    
    if len(batch_data) < MIN_PRESENTATIONS:
        return {
            "updated": False,
            "audience_group": audience_group,
            "presentation_count": presentation_count,
            "reason": "완성된 발표 배치가 없습니다."
        }
        
    if old_weights is None:
        old_weights = DEFAULT_WEIGHT.copy()

    if current_thresholds is None:
        current_thresholds = DEFAULT_THRESHOLD.copy()
        
    correlations = feature_corr(batch_data)
    target_weights = correlation_to_weights(correlations)
    updated_weights = update_weights(old_weights=old_weights, target_weights=target_weights)
    
    directions = analyze_feature_direction(correlations)
    # 임계치 업데이트
    # updated_thresholds = update_thresholds(current_thresholds=current_thresholds,correlations=correlations)
    
    return {
        "updated": True,
        "audience_group": audience_group,

        "presentation_count": presentation_count,

        "batch_index": batch_index,

        "batch_start": start_index,
        "batch_end": end_index - 1,

        "batch_size": len(batch_data),

        "correlations": correlations,
        "directions": directions,
        "old_weights": old_weights,
        "target_weights": target_weights,
        "updated_weights": updated_weights,

        # "old_thresholds": current_thresholds,
        # "updated_thresholds": updated_thresholds
    }