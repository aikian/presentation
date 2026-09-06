from typing import Any, Dict

import pandas as pd
from pandas import DataFrame
from scipy.stats import spearmanr

'''
음성 특징 정규화 -> 스피어만 상관게수 -> 가중치 조정
전체 발표 시간 대비 군말횟수
임계치 업데이트 공식 
New_threshold = Current_threshold + (learning_rate*ErrorRate*Current_threshold)
'''

'''
각 발표에 대한 속성과 집중도 평균 구해서 데이터베이스에 저장
저장된 데이터가 10개 이상이면 가중치와 임계치 업데이트

청중 설문 데이터로 스피어만 상관계수 구하기
스피어만 상관계수로 가중치 업데이트
가중치 업데이트
target_weight = DEFAULT_WEIGHT * abs(rho)
new_weight = old_weight + learning_rate * (
    target_weight - old_weight
)

임계치 업데이트
error = predicted_attention - actual_attention
delta = learning_rate * error * abs(rho)
new_threshold = old_threshold + direction * delta 
 -> direction은 규칙에 따라서

'''

LEARNING_RATE = 0.1 # 학습률 지정

MIN_PRESENTATIONS = 10 # 가중치 업데이트에 필요한 최소 발표 수

FEATURES = [
    "spm_mean",
    "pitch_mean",
    "db_mean",
    "silence_mean",
    "filler_mean",
    "monotony_mean",
]

TARGET = "attention_mean"

# 초기 가중치
# DB에 저장 후 가져와서 사용하도록 수정 필요
DEFAULT_WEIGHT: Dict[str, float] = {
    "spm_penalty_weight" : 0.2,
    "pitch_penalty_weight" : 0.2,
    "db_boost_weight" : 0.2,
    "silence_penalty_weight" : 0.2,
    "filler_penalty_weight" : 0.2,
    "monotone_penalty_weight" : 0.2,
}

DEFAULT_THRESHOLD: Dict[str, float] = {
    "fast_spm_threshold": 350.0,
    "slow_spm_threshold": 250.0,
    "silence_penalty_threshold": 5.0,
    "filler_60sec_limit": 5.0,
    "monotone_penalty_threshold": 0.08,
    "excessive_pitch_threshold": 0.25,
}

FEATURE_WEIGHT_KEY = {
    "spm_mean": "spm_penalty_weight",
    "pitch_mean": "pitch_penalty_weight",
    "db_mean": "db_boost_weight",
    "silence_mean": "silence_penalty_weight",
    "filler_mean": "filler_penalty_weight",
    "monotony_mean": "monotone_penalty_weight",
}

FEATURE_THRESHOLD_KEY = {
    "spm_mean": ["fast_spm_threshold", "slow_spm_threshold"],
    "pitch_mean": ["excessive_pitch_threshold"],
    "silence_mean": ["silence_penalty_threshold"],
    "filler_mean": ["filler_60sec_limit"],
    "monotony_mean": ["monotone_penalty_threshold"],
}

# 청중의 설문 데이터를 기반으로 각 속성들과의 스피어만 상관계수 계산
def calculate_spearmanr(result: DataFrame, feature: str) -> Dict[str, Any]:
    
    data = result[[feature, TARGET]].dropna()
    
    sample_length = len(data)
    
    if sample_length == 0:
        return {
            "correlation": None,
            "p_value": None,
            "sample_size": 0,
            "updated": False,
            "reason": "유효한 데이터가 없습니다."
        }
        
    if data[feature].nunique() <= 1:
        return {
            "correlation": 0.0,
            "p_value": 1.0,
            "sample_size": sample_length,
            "updated": False,
            "reason": f"'{feature}' 값의 변화가 없습니다.",
        }

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
    absolute_correlations: Dict[str, float] = {}
    result: Dict[str, float] = {}
    
    for feature in FEATURES:
        result = correlations.get(feature, {})
        correlation = result.get("correlation") 
        
        if correlation is None:
            continue
        
        absolute_correlations[feature] = abs(float(correlation))

    total = sum(absolute_correlations.values())
    
    if total <= 0:
        for feature in FEATURES:
            result[feature] = 1 / len(FEATURES)
            
    else:
        for feature in FEATURES:
            result[feature] = absolute_correlations.get(feature, 0.0) / total
            
    return result

def update_weights(old_weights: Dict[str, float], target_weights: Dict[str, float]) -> Dict[str, float]:
    updated_weights = {}
    
    for feature in FEATURES:
        
        weight_key = FEATURE_WEIGHT_KEY[feature]
        
        old_weight = old_weights.get(weight_key, 0.0)
        target_weight = target_weights.get(weight_key, 0.0)

        updated_weights[weight_key] = (old_weight + LEARNING_RATE * (target_weight - old_weight))
    
    # 업데이트 후에도 가중치 합이 1이 되도록 정규화
    total = sum(updated_weights.values())
    
    if total > 0:
        for key, value in updated_weights:
            updated_weights[key] = value / total
    
    return updated_weights        

# DB에 저장하도록 코드 수정 필요
def update_group_weight(presentation_data: DataFrame, audience_group: str, old_weights: Dict[str, float] | None = None) -> Dict[str, Any]:
    
    # 특정 청중 그룹의 발표가 10개 이상 쌓이면 해당 그룹의 가중치 업데이트
    
    group_data = presentation_data[presentation_data["audience_group"]== audience_group].copy
    
    presentation_count = len(group_data)
    if presentation_count < MIN_PRESENTATIONS:
        return {
            "updated": False,
            "audience_group": audience_group,
            "presentation_count": presentation_count,
            "reason": (f"{audience_group} 그룹의 발표 데이터가 {MIN_PRESENTATIONS}개 미만입니다.")
        }
    
    if old_weights is None:
        old_weights = DEFAULT_WEIGHT.copy()
    
    correlations = feature_corr(group_data)
    target_weights = correlation_to_weights(correlations)
    
    updated_weights = update_weights(old_weights, target_weights)
    
    return {
        "updated": True,
        "audience_group": audience_group,
        "presentation_count": presentation_count,
        "correlations": correlations,
        "old_weights": old_weights,
        "updated_weights": updated_weights,
    }

'''
def update_threshold(df: DataFrame, corr: Dict[str, Any]):
    actual_attention = df['attention']
    error = predicted_attention - actual_attention
    delta = learning_rate * error * abs(corr)
    #
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
            "reason": (f"{audience_group} 그룹의 발표 데이터가 {MIN_PRESENTATIONS}개 미만입니다."),
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
            "reason": "완성된 발표 배치가 없습니다.",
        }
        
    if old_weights is None:
        old_weights = DEFAULT_WEIGHT.copy()

    if current_thresholds is None:
        current_thresholds = DEFAULT_THRESHOLD.copy()
        
    correlations = feature_corr(batch_data)
    target_weights = correlation_to_weights(correlations)
    updated_weights = update_weights(old_weights=old_weights, target_weights=target_weights)
    
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

        "old_weights": old_weights,
        "target_weights": target_weights,
        "updated_weights": updated_weights,

        # "old_thresholds": current_thresholds,
        # "updated_thresholds": updated_thresholds,
    }