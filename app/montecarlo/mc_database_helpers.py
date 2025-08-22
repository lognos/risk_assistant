import pandas as pd
from typing import List, Dict, Any


def _coerce_to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
	if not rows:
		return pd.DataFrame()
	return pd.DataFrame(rows)


def normalize_capex_items(rows: List[Dict[str, Any]]) -> pd.DataFrame:
	df = _coerce_to_df(rows)
	if df.empty:
		return df
	# Standardize column names if needed
	rename_map = {
		"id": "item_id",
		"name": "item_name",
		"min": "min_cost",
		"ml": "ml_cost",
		"max": "max_cost",
	}
	for k, v in rename_map.items():
		if k in df.columns and v not in df.columns:
			df = df.rename(columns={k: v})
	# Ensure required columns exist
	for col in ["item_id", "item_name", "min_cost", "ml_cost", "max_cost"]:
		if col not in df.columns:
			df[col] = pd.Series(dtype="float64" if "cost" in col else "object")
	return df


def normalize_capex_actions(rows: List[Dict[str, Any]]) -> pd.DataFrame:
	df = _coerce_to_df(rows)
	if df.empty:
		return df
	rename_map = {
		"id": "cost_action_id",
		"name": "cost_action_name",
		"due": "cost_action_due",
		"pm_min": "pm_min_cost",
		"pm_ml": "pm_ml_cost",
		"pm_max": "pm_max_cost",
	}
	for k, v in rename_map.items():
		if k in df.columns and v not in df.columns:
			df = df.rename(columns={k: v})
	# Coerce dates to datetime if present
	if "cost_action_due" in df.columns:
		df["cost_action_due"] = pd.to_datetime(df["cost_action_due"], errors="coerce")
	return df


def normalize_risks(rows: List[Dict[str, Any]]) -> pd.DataFrame:
	df = _coerce_to_df(rows)
	if df.empty:
		return df
	rename_map = {
		"id": "risk_id",
		"name": "risk_name",
		"min": "min_impact",
		"ml": "ml_impact",
		"max": "max_impact",
		"prob": "risk_probability",
		"log": "risk_log",
	}
	for k, v in rename_map.items():
		if k in df.columns and v not in df.columns:
			df = df.rename(columns={k: v})
	if "risk_log" in df.columns:
		df["risk_log"] = pd.to_datetime(df["risk_log"], errors="coerce")
	return df


def normalize_risk_actions(rows: List[Dict[str, Any]]) -> pd.DataFrame:
	df = _coerce_to_df(rows)
	if df.empty:
		return df
	rename_map = {
		"id": "risk_action_id",
		"name": "risk_action_name",
		"due": "risk_action_due",
		"pm_min": "pm_min_impact",
		"pm_ml": "pm_ml_impact",
		"pm_max": "pm_max_impact",
		"pm_prob": "pm_risk_probability",
	}
	for k, v in rename_map.items():
		if k in df.columns and v not in df.columns:
			df = df.rename(columns={k: v})
	if "risk_action_due" in df.columns:
		df["risk_action_due"] = pd.to_datetime(df["risk_action_due"], errors="coerce")
	return df

