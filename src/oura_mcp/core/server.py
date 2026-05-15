"""MCP Server implementation for Oura Ring data."""

import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..api.client import OuraClient
from ..utils.config import Config, get_config
from ..utils.logging import get_logger, setup_logging
from ..utils.baselines import BaselineManager
from ..utils.anomalies import AnomalyDetector
from ..utils.interpretation import InterpretationEngine
from ..resources.formatters import HealthDataFormatter
from ..resources.health_resources import HealthResourceProvider
from ..resources.metrics_resources import MetricsResourceProvider
from ..tools.data_tools import DataToolProvider
from ..tools.intelligence_tools import IntelligenceToolProvider
from ..tools.debug_tools import DebugToolProvider
from ..tools.analytics_tools import AnalyticsToolProvider
from ..tools.prediction_tools import PredictionToolProvider


logger = get_logger(__name__)


class OuraMCPServer:
    """
    MCP Server for Oura Ring data.
    
    Provides resources and tools for AI assistants to access
    and analyze health metrics.
    """
    
    def __init__(self, config: Config):
        """
        Initialize MCP server.

        Args:
            config: Server configuration
        """
        self.config = config
        self.server = Server(config.mcp.server.name)
        self.oura_client: OuraClient = None

        # Initialize intelligence components
        self.baseline_manager = BaselineManager()
        self.anomaly_detector = AnomalyDetector(self.baseline_manager)
        self.interpreter = InterpretationEngine()

        # Initialize formatter
        self.formatter = HealthDataFormatter(
            self.baseline_manager,
            self.interpreter
        )

        # Initialize resource providers (will be fully initialized after client is ready)
        self.health_resources = None
        self.metrics_resources = None

        # Initialize tool providers (will be fully initialized after client is ready)
        self.data_tools = None
        self.intelligence_tools = None
        self.debug_tools = None
        self.analytics_tools = None
        self.prediction_tools = None

        # Register handlers
        self._register_resources()
        self._register_tools()

        logger.info(f"Initialized {config.mcp.server.name} v{config.mcp.server.version}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize Oura client
        self.oura_client = OuraClient(self.config.oura.api)
        await self.oura_client.__aenter__()

        # Initialize resource providers
        self.health_resources = HealthResourceProvider(
            self.oura_client,
            self.formatter
        )
        self.metrics_resources = MetricsResourceProvider(
            self.oura_client
        )

        # Initialize tool providers
        self.data_tools = DataToolProvider(self.oura_client)
        self.intelligence_tools = IntelligenceToolProvider(
            self.oura_client,
            self.baseline_manager,
            self.anomaly_detector,
            self.interpreter
        )
        self.debug_tools = DebugToolProvider(self.oura_client)
        self.analytics_tools = AnalyticsToolProvider(self.oura_client)
        self.prediction_tools = PredictionToolProvider(self.oura_client)

        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.oura_client:
            await self.oura_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.server.list_resources()
        async def list_resources():
            """List available resources."""
            resources = []
            
            if "sleep" in self.config.mcp.resources.enabled:
                resources.extend([
                    {
                        "uri": "oura://sleep/today",
                        "name": "Today's Sleep",
                        "mimeType": "application/json",
                        "description": "Sleep data for last night"
                    },
                    {
                        "uri": "oura://sleep/yesterday",
                        "name": "Yesterday's Sleep",
                        "mimeType": "application/json",
                        "description": "Sleep data from the night before"
                    },
                ])
            
            if "readiness" in self.config.mcp.resources.enabled:
                resources.append({
                    "uri": "oura://readiness/today",
                    "name": "Today's Readiness",
                    "mimeType": "application/json",
                    "description": "Readiness score and contributing factors"
                })
            
            if "activity" in self.config.mcp.resources.enabled:
                resources.append({
                    "uri": "oura://activity/today",
                    "name": "Today's Activity",
                    "mimeType": "application/json",
                    "description": "Activity data for today"
                })

            if "hrv" in self.config.mcp.resources.enabled:
                resources.extend([
                    {
                        "uri": "oura://hrv/latest",
                        "name": "Latest HRV",
                        "mimeType": "application/json",
                        "description": "Most recent HRV data with baseline comparison"
                    },
                    {
                        "uri": "oura://hrv/trend/7_days",
                        "name": "HRV Trend (7 days)",
                        "mimeType": "application/json",
                        "description": "HRV trend over last 7 days"
                    },
                    {
                        "uri": "oura://hrv/trend/30_days",
                        "name": "HRV Trend (30 days)",
                        "mimeType": "application/json",
                        "description": "HRV trend over last 30 days"
                    }
                ])

            # Add personal info resource
            resources.append({
                "uri": "oura://personal_info",
                "name": "Personal Information",
                "mimeType": "application/json",
                "description": "User profile (age, weight, height, biological sex)"
            })

            # Add stress resource
            resources.append({
                "uri": "oura://stress/today",
                "name": "Today's Stress",
                "mimeType": "application/json",
                "description": "Daytime stress levels and recovery time"
            })

            # Add SpO2 resource
            resources.append({
                "uri": "oura://spo2/latest",
                "name": "Latest SpO2",
                "mimeType": "application/json",
                "description": "Blood oxygen saturation during sleep"
            })

            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str):
            """Read a specific resource."""
            logger.info(f"Reading resource: {uri}")
            
            try:
                # Parse URI
                if uri.startswith("oura://sleep/"):
                    period = uri.split("/")[-1]
                    return await self._get_sleep_resource(period)
                
                elif uri.startswith("oura://readiness/"):
                    period = uri.split("/")[-1]
                    return await self._get_readiness_resource(period)
                
                elif uri.startswith("oura://activity/"):
                    period = uri.split("/")[-1]
                    return await self._get_activity_resource(period)

                elif uri.startswith("oura://hrv/"):
                    # Parse: oura://hrv/latest or oura://hrv/trend/7_days
                    parts = uri.replace("oura://hrv/", "").split("/")
                    if parts[0] == "latest":
                        return await self._get_hrv_resource("latest")
                    elif parts[0] == "trend":
                        period = parts[1] if len(parts) > 1 else "7_days"
                        return await self._get_hrv_resource(f"trend_{period}")
                    else:
                        raise ValueError(f"Unknown HRV resource: {uri}")

                elif uri == "oura://personal_info":
                    return await self._get_personal_info_resource()

                elif uri.startswith("oura://stress/"):
                    period = uri.split("/")[-1]
                    return await self._get_stress_resource(period)

                elif uri.startswith("oura://spo2/"):
                    period = uri.split("/")[-1]
                    return await self._get_spo2_resource(period)

                else:
                    raise ValueError(f"Unknown resource URI: {uri}")
            
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise
    
    def _register_tools(self):
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            tools = []

            if "generate_daily_brief" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="generate_daily_brief",
                    description="Generate comprehensive daily health brief",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    }
                ))

            # Add weekly report tool
            tools.append(types.Tool(
                name="generate_weekly_report",
                description="Generate comprehensive weekly health report with trends, highlights, and recommendations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "weeks_ago": {
                            "type": "integer",
                            "description": "Number of weeks ago to report (0 = current week, 1 = last week)",
                            "default": 0
                        },
                        "include_previous_week": {
                            "type": "boolean",
                            "description": "Include week-over-week comparison",
                            "default": True
                        }
                    }
                }
            ))

            if "analyze_sleep_trend" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="analyze_sleep_trend",
                    description="Analyze sleep patterns over specified period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "Number of days to analyze",
                                "default": 7
                            }
                        }
                    }
                ))

            if "detect_recovery_status" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="detect_recovery_status",
                    description="Assess current recovery state based on multiple physiological signals",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    }
                ))

            if "assess_training_readiness" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="assess_training_readiness",
                    description="Assess readiness for specific types of training",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "training_type": {
                                "type": "string",
                                "description": "Type of training: general, endurance, strength, high_intensity",
                                "enum": ["general", "endurance", "strength", "high_intensity"],
                                "default": "general"
                            }
                        }
                    }
                ))

            if "correlate_metrics" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="correlate_metrics",
                    description="Find correlations between two metrics over specified period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric1": {
                                "type": "string",
                                "description": "First metric (e.g., 'activity_score', 'sleep_score', 'hrv_balance')"
                            },
                            "metric2": {
                                "type": "string",
                                "description": "Second metric (e.g., 'readiness_score', 'resting_heart_rate')"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to analyze",
                                "default": 30
                            }
                        },
                        "required": ["metric1", "metric2"]
                    }
                ))

            if "detect_anomalies" in self.config.mcp.tools.enabled:
                tools.append(types.Tool(
                    name="detect_anomalies",
                    description="Detect statistical anomalies in metrics over recent period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric_type": {
                                "type": "string",
                                "description": "Type of metric to analyze: sleep, readiness, activity",
                                "enum": ["sleep", "readiness", "activity"],
                                "default": "sleep"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to analyze",
                                "default": 7
                            }
                        }
                    }
                ))

            # HRV raw values in milliseconds from detailed sleep endpoint
            tools.append(types.Tool(
                name="get_hrv_trend",
                description="Get raw HRV values in milliseconds (average_hrv from sleep endpoint) with resting HR and sleep stages — use for trend analysis over days/weeks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 30
                        }
                    }
                }
            ))

            # Add debug tool to see raw data
            tools.append(types.Tool(
                name="get_raw_sleep_data",
                description="Get raw sleep data from Oura API for debugging (shows last N days)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 3
                        }
                    }
                }
            ))

            # Add detailed sleep sessions tool
            tools.append(types.Tool(
                name="get_sleep_sessions",
                description="Get detailed sleep sessions with exact times and durations (includes all sleep periods like naps, couch sleep, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 3
                        }
                    }
                }
            ))

            # Add heart rate tool
            tools.append(types.Tool(
                name="get_heart_rate_data",
                description="Get time-series heart rate data with HR zones and patterns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to retrieve",
                            "default": 24
                        }
                    }
                }
            ))

            # Add workout sessions tool
            tools.append(types.Tool(
                name="get_workout_sessions",
                description="Get detailed workout/activity sessions with HR data and metrics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 7
                        }
                    }
                }
            ))

            # Add daily stress tool
            tools.append(types.Tool(
                name="get_daily_stress",
                description="Get daily stress levels, stress load, and recovery time",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 7
                        }
                    }
                }
            ))

            # Add SpO2 tool
            tools.append(types.Tool(
                name="get_spo2_data",
                description="Get blood oxygen saturation (SpO2) data during sleep",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 7
                        }
                    }
                }
            ))

            # Add VO2 Max tool
            tools.append(types.Tool(
                name="get_vo2_max",
                description="Get VO2 Max (cardiorespiratory fitness) estimates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 30
                        }
                    }
                }
            ))

            # Add tags tool
            tools.append(types.Tool(
                name="get_tags",
                description="Get user-created tags and notes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to retrieve",
                            "default": 7
                        }
                    }
                }
            ))

            # Add analytics tool
            tools.append(types.Tool(
                name="generate_statistics_report",
                description="Generate comprehensive statistical analysis of health data with trends, patterns, and insights",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 30
                        }
                    }
                }
            ))

            # Add prediction tools
            tools.append(types.Tool(
                name="predict_sleep_quality",
                description="Predict sleep quality for upcoming days using multiple forecasting methods (trend, moving average, weekly patterns)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to predict",
                            "default": 3
                        }
                    }
                }
            ))

            tools.append(types.Tool(
                name="predict_readiness",
                description="Forecast readiness scores and training recommendations for upcoming days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to predict",
                            "default": 3
                        }
                    }
                }
            ))

            tools.append(types.Tool(
                name="predict_calorie_needs",
                description="Predict daily calorie needs (TDEE) for upcoming days based on activity patterns, with personalized macro recommendations. You can either use a predefined nutrition style OR specify a custom max carbs limit.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to predict",
                            "default": 7
                        },
                        "nutrition_style": {
                            "type": "string",
                            "description": "Nutrition approach for macro recommendations (ignored if max_carbs_g is set)",
                            "enum": ["balanced", "keto", "low_carb", "carnivore", "paleo", "high_protein", "athlete", "mediterranean", "zone"],
                            "default": "balanced"
                        },
                        "max_carbs_g": {
                            "type": "integer",
                            "description": "Maximum carbs in grams per day (overrides nutrition_style if provided). Example: 30 for very low carb, 50 for keto, 100 for low carb"
                        }
                    }
                }
            ))

            # Add sleep debt tool
            tools.append(types.Tool(
                name="analyze_sleep_debt",
                description="Calculate accumulated sleep debt over time with severity assessment and recovery recommendations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 30
                        }
                    }
                }
            ))

            # Add optimal bedtime calculator tool
            tools.append(types.Tool(
                name="calculate_optimal_bedtime",
                description="Calculate optimal bedtime based on analysis of your best sleep nights",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 30
                        },
                        "top_percentile": {
                            "type": "number",
                            "description": "Fraction of best nights to analyze (e.g., 0.25 = top 25%)",
                            "default": 0.25
                        }
                    }
                }
            ))

            # Add supplement correlation tool
            tools.append(types.Tool(
                name="analyze_supplement_correlation",
                description="Analyze correlation between tags (supplements, interventions) and sleep/health metrics to identify what works",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 60
                        },
                        "min_occurrences": {
                            "type": "integer",
                            "description": "Minimum number of tag occurrences to analyze",
                            "default": 3
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "Number of top results to show in detail",
                            "default": 10
                        }
                    }
                }
            ))

            # Add health alerts tool
            tools.append(types.Tool(
                name="check_health_alerts",
                description="Check for critical health alerts and warnings based on recent metrics and trends",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lookback_days": {
                            "type": "integer",
                            "description": "Number of days to analyze for alerts",
                            "default": 7
                        }
                    }
                }
            ))

            # Add illness detection tool
            tools.append(types.Tool(
                name="detect_illness_risk",
                description="Early illness detection using multi-signal analysis (temperature, HRV, resting HR, respiratory rate). Provides 1-2 day advance warning",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lookback_days": {
                            "type": "integer",
                            "description": "Number of days for baseline calculation",
                            "default": 30
                        }
                    }
                }
            ))

            # Add chronotype analysis tool
            tools.append(types.Tool(
                name="analyze_chronotype",
                description="Analyze chronotype (morning lark, night owl, intermediate) based on sleep timing patterns, sleep quality by bedtime, and activity patterns. Provides personalized recommendations for optimal work hours and exercise timing",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lookback_days": {
                            "type": "integer",
                            "description": "Number of days to analyze (minimum 14, recommended 30+)",
                            "default": 30
                        },
                        "include_activity": {
                            "type": "boolean",
                            "description": "Include activity pattern analysis",
                            "default": True
                        }
                    }
                }
            ))

            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            """Execute a tool."""
            logger.info(f"Calling tool: {name} with args: {arguments}")

            try:
                if name == "generate_daily_brief":
                    result = await self._tool_generate_daily_brief()
                    return [types.TextContent(type="text", text=result)]

                elif name == "generate_weekly_report":
                    weeks_ago = arguments.get("weeks_ago", 0)
                    include_previous_week = arguments.get("include_previous_week", True)
                    result = await self._tool_generate_weekly_report(weeks_ago, include_previous_week)
                    return [types.TextContent(type="text", text=result)]

                elif name == "analyze_sleep_trend":
                    days = arguments.get("days", 7)
                    result = await self._tool_analyze_sleep_trend(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_raw_sleep_data":
                    days = arguments.get("days", 3)
                    result = await self._tool_get_raw_sleep_data(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "detect_recovery_status":
                    result = await self._tool_detect_recovery_status()
                    return [types.TextContent(type="text", text=result)]

                elif name == "assess_training_readiness":
                    training_type = arguments.get("training_type", "general")
                    result = await self._tool_assess_training_readiness(training_type)
                    return [types.TextContent(type="text", text=result)]

                elif name == "correlate_metrics":
                    metric1 = arguments.get("metric1")
                    metric2 = arguments.get("metric2")
                    days = arguments.get("days", 30)
                    result = await self._tool_correlate_metrics(metric1, metric2, days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "detect_anomalies":
                    metric_type = arguments.get("metric_type", "sleep")
                    days = arguments.get("days", 7)
                    result = await self._tool_detect_anomalies(metric_type, days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_hrv_trend":
                    days = arguments.get("days", 30)
                    result = await self._tool_get_hrv_trend(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_sleep_sessions":
                    days = arguments.get("days", 3)
                    result = await self._tool_get_sleep_sessions(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_heart_rate_data":
                    hours = arguments.get("hours", 24)
                    result = await self._tool_get_heart_rate_data(hours)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_workout_sessions":
                    days = arguments.get("days", 7)
                    result = await self._tool_get_workout_sessions(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_daily_stress":
                    days = arguments.get("days", 7)
                    result = await self._tool_get_daily_stress(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_spo2_data":
                    days = arguments.get("days", 7)
                    result = await self._tool_get_spo2_data(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_vo2_max":
                    days = arguments.get("days", 30)
                    result = await self._tool_get_vo2_max(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "get_tags":
                    days = arguments.get("days", 7)
                    result = await self._tool_get_tags(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "generate_statistics_report":
                    days = arguments.get("days", 30)
                    result = await self._tool_generate_statistics_report(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "predict_sleep_quality":
                    days_ahead = arguments.get("days_ahead", 3)
                    result = await self._tool_predict_sleep_quality(days_ahead)
                    return [types.TextContent(type="text", text=result)]

                elif name == "predict_readiness":
                    days_ahead = arguments.get("days_ahead", 3)
                    result = await self._tool_predict_readiness(days_ahead)
                    return [types.TextContent(type="text", text=result)]

                elif name == "predict_calorie_needs":
                    days_ahead = arguments.get("days_ahead", 7)
                    nutrition_style = arguments.get("nutrition_style", "balanced")
                    max_carbs_g = arguments.get("max_carbs_g")
                    result = await self._tool_predict_calorie_needs(days_ahead, nutrition_style, max_carbs_g)
                    return [types.TextContent(type="text", text=result)]

                elif name == "analyze_sleep_debt":
                    days = arguments.get("days", 30)
                    result = await self._tool_analyze_sleep_debt(days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "calculate_optimal_bedtime":
                    days = arguments.get("days", 30)
                    top_percentile = arguments.get("top_percentile", 0.25)
                    result = await self._tool_calculate_optimal_bedtime(days, top_percentile)
                    return [types.TextContent(type="text", text=result)]

                elif name == "analyze_supplement_correlation":
                    days = arguments.get("days", 60)
                    min_occurrences = arguments.get("min_occurrences", 3)
                    top_n = arguments.get("top_n", 10)
                    result = await self._tool_analyze_supplement_correlation(days, min_occurrences, top_n)
                    return [types.TextContent(type="text", text=result)]

                elif name == "check_health_alerts":
                    lookback_days = arguments.get("lookback_days", 7)
                    result = await self._tool_check_health_alerts(lookback_days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "detect_illness_risk":
                    lookback_days = arguments.get("lookback_days", 30)
                    result = await self._tool_detect_illness_risk(lookback_days)
                    return [types.TextContent(type="text", text=result)]

                elif name == "analyze_chronotype":
                    lookback_days = arguments.get("lookback_days", 30)
                    include_activity = arguments.get("include_activity", True)
                    result = await self._tool_analyze_chronotype(lookback_days, include_activity)
                    return [types.TextContent(type="text", text=result)]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                raise
    
    # === Resource Implementations ===
    
    async def _get_sleep_resource(self, period: str) -> str:
        """Get sleep resource data."""
        return await self.health_resources.get_sleep_resource(period)
    
    async def _get_readiness_resource(self, period: str) -> str:
        """Get readiness resource data."""
        return await self.health_resources.get_readiness_resource(period)
    
    async def _get_activity_resource(self, period: str) -> str:
        """Get activity resource data."""
        return await self.health_resources.get_activity_resource(period)

    async def _get_hrv_resource(self, period: str) -> str:
        """Get HRV resource data with baseline comparison."""
        return await self.health_resources.get_hrv_resource(period)

    async def _get_personal_info_resource(self) -> str:
        """Get personal information resource."""
        return await self.metrics_resources.get_personal_info_resource()

    async def _get_stress_resource(self, period: str) -> str:
        """Get stress resource data."""
        return await self.metrics_resources.get_stress_resource(period)

    async def _get_spo2_resource(self, period: str) -> str:
        """Get SpO2 resource data."""
        return await self.metrics_resources.get_spo2_resource(period)

    # === Tool Implementations (delegated to providers) ===

    # Debug tools
    async def _tool_generate_daily_brief(self) -> str:
        """Generate daily health brief."""
        return await self.debug_tools.generate_daily_brief()

    async def _tool_generate_weekly_report(self, weeks_ago: int, include_previous_week: bool) -> str:
        """Generate weekly health report."""
        return await self.debug_tools.generate_weekly_report(weeks_ago, include_previous_week)

    async def _tool_analyze_sleep_trend(self, days: int) -> str:
        """Analyze sleep trend."""
        return await self.debug_tools.analyze_sleep_trend(days)

    async def _tool_get_hrv_trend(self, days: int) -> str:
        """Get raw HRV values in ms from detailed sleep endpoint."""
        return await self.debug_tools.get_hrv_trend(days)

    async def _tool_get_raw_sleep_data(self, days: int) -> str:
        """Get raw sleep data from Oura API for debugging."""
        return await self.debug_tools.get_raw_sleep_data(days)

    async def _tool_get_sleep_sessions(self, days: int) -> str:
        """Get detailed sleep sessions with exact times and durations."""
        return await self.data_tools.get_sleep_sessions(days)

    async def _tool_get_heart_rate_data(self, hours: int) -> str:
        """Get time-series heart rate data."""
        return await self.data_tools.get_heart_rate_data(hours)

    async def _tool_get_workout_sessions(self, days: int) -> str:
        """Get detailed workout sessions."""
        return await self.data_tools.get_workout_sessions(days)

    async def _tool_get_daily_stress(self, days: int) -> str:
        """Get daily stress data."""
        return await self.data_tools.get_daily_stress(days)

    async def _tool_get_spo2_data(self, days: int) -> str:
        """Get SpO2 (blood oxygen saturation) data."""
        return await self.data_tools.get_spo2_data(days)

    async def _tool_get_vo2_max(self, days: int) -> str:
        """Get VO2 Max data."""
        return await self.data_tools.get_vo2_max(days)

    async def _tool_get_tags(self, days: int) -> str:
        """Get user-created tags."""
        return await self.data_tools.get_tags(days)

    async def _tool_generate_statistics_report(self, days: int) -> str:
        """Generate comprehensive statistics report."""
        return await self.analytics_tools.generate_statistics_report(days)

    async def _tool_predict_sleep_quality(self, days_ahead: int) -> str:
        """Predict sleep quality for upcoming days."""
        return await self.prediction_tools.predict_sleep_quality(days_ahead)

    async def _tool_predict_readiness(self, days_ahead: int) -> str:
        """Predict readiness for upcoming days."""
        return await self.prediction_tools.predict_readiness(days_ahead)

    async def _tool_predict_calorie_needs(
        self,
        days_ahead: int,
        nutrition_style: str = "balanced",
        max_carbs_g: Optional[int] = None
    ) -> str:
        """Predict daily calorie needs for upcoming days."""
        return await self.prediction_tools.predict_calorie_needs(days_ahead, nutrition_style, max_carbs_g)

    async def _tool_analyze_sleep_debt(self, days: int) -> str:
        """Analyze accumulated sleep debt."""
        return await self.analytics_tools.analyze_sleep_debt(days)

    async def _tool_calculate_optimal_bedtime(self, days: int, top_percentile: float) -> str:
        """Calculate optimal bedtime based on best nights."""
        return await self.intelligence_tools.calculate_optimal_bedtime(days, top_percentile)

    async def _tool_analyze_supplement_correlation(self, days: int, min_occurrences: int, top_n: int) -> str:
        """Analyze supplement/tag correlation with health metrics."""
        return await self.analytics_tools.analyze_supplement_correlation(days, min_occurrences, top_n)

    async def _tool_check_health_alerts(self, lookback_days: int) -> str:
        """Check for critical health alerts and warnings."""
        return await self.intelligence_tools.check_health_alerts(lookback_days)

    async def _tool_detect_illness_risk(self, lookback_days: int) -> str:
        """Detect illness risk using multi-signal analysis."""
        return await self.intelligence_tools.detect_illness_risk(lookback_days)

    async def _tool_analyze_chronotype(self, lookback_days: int, include_activity: bool) -> str:
        """Analyze chronotype and provide personalized recommendations."""
        return await self.intelligence_tools.analyze_chronotype(lookback_days, include_activity)

    async def _tool_detect_recovery_status(self) -> str:
        """Detect current recovery status based on multiple signals."""
        return await self.intelligence_tools.detect_recovery_status()

    async def _tool_assess_training_readiness(self, training_type: str) -> str:
        """Assess readiness for specific training type."""
        return await self.intelligence_tools.assess_training_readiness(training_type)

    async def _tool_correlate_metrics(self, metric1: str, metric2: str, days: int) -> str:
        """Find correlations between two metrics."""
        return await self.intelligence_tools.correlate_metrics(metric1, metric2, days)

    async def _tool_detect_anomalies(self, metric_type: str, days: int) -> str:
        """Detect anomalies in specified metric type."""
        return await self.intelligence_tools.detect_anomalies(metric_type, days)

    # === Semantic Formatters ===

    def _format_sleep_semantic_detailed(
        self,
        day: str,
        score: int,
        contributors: Dict[str, int],
        total_sleep: int,
        deep_sleep: int,
        rem_sleep: int,
        light_sleep: int,
        awake_time: int,
        periods_count: int
    ) -> str:
        """Format detailed sleep data semantically."""
        result = f"# Sleep Report\n\n"
        result += f"**Date:** {day}\n"
        result += f"**Score:** {score}/100\n\n"

        # Check if we have actual data
        if total_sleep == 0:
            result += "*Note: Sleep data not yet fully synchronized*\n\n"
            return result

        # Duration breakdown
        hours = total_sleep // 3600
        minutes = (total_sleep % 3600) // 60
        result += f"## Total Sleep: {hours}h {minutes}m\n\n"

        if periods_count > 1:
            result += f"*Recorded across {periods_count} sleep periods (biphasic/polyphasic)*\n\n"

        # Sleep stages
        result += f"## Sleep Stages\n\n"

        if total_sleep > 0:
            deep_pct = (deep_sleep / total_sleep * 100) if deep_sleep > 0 else 0
            rem_pct = (rem_sleep / total_sleep * 100) if rem_sleep > 0 else 0
            light_pct = (light_sleep / total_sleep * 100) if light_sleep > 0 else 0
            awake_pct = (awake_time / total_sleep * 100) if awake_time > 0 else 0

            result += f"- **Deep Sleep:** {deep_sleep // 60}m ({deep_pct:.1f}%)\n"
            result += f"- **REM Sleep:** {rem_sleep // 60}m ({rem_pct:.1f}%)\n"
            result += f"- **Light Sleep:** {light_sleep // 60}m ({light_pct:.1f}%)\n"
            result += f"- **Awake Time:** {awake_time // 60}m ({awake_pct:.1f}%)\n\n"

        # Contributors (scores)
        if contributors:
            result += f"## Sleep Quality Scores\n\n"
            contributor_names = {
                "total_sleep": "Total Sleep Duration",
                "deep_sleep": "Deep Sleep Quality",
                "rem_sleep": "REM Sleep Quality",
                "efficiency": "Sleep Efficiency",
                "restfulness": "Restfulness",
                "latency": "Sleep Latency",
                "timing": "Sleep Timing"
            }

            for key, name in contributor_names.items():
                if key in contributors:
                    value = contributors[key]
                    result += f"- **{name}:** {value}/100\n"

        return result

    def _format_sleep_semantic(self, data: Dict[str, Any]) -> str:
        """Format sleep data semantically."""
        score = data.get("score", 0)
        total_sleep = data.get("total_sleep_duration", 0)
        deep_sleep = data.get("deep_sleep_duration", 0)
        rem_sleep = data.get("rem_sleep_duration", 0)

        result = f"# Sleep Report\n\n"
        result += f"**Date:** {data.get('day')}\n"
        result += f"**Score:** {score}/100\n\n"
        result += f"## Duration\n"
        result += f"- Total: {total_sleep // 3600}h {(total_sleep % 3600) // 60}m\n"

        # Only show percentages if total_sleep > 0
        if total_sleep > 0:
            result += f"- Deep: {deep_sleep // 60}m ({deep_sleep / total_sleep * 100:.1f}%)\n"
            result += f"- REM: {rem_sleep // 60}m ({rem_sleep / total_sleep * 100:.1f}%)\n"
        else:
            result += f"- Deep: {deep_sleep // 60}m\n"
            result += f"- REM: {rem_sleep // 60}m\n"
            result += "\n*Note: Sleep data not yet fully synchronized*\n"

        return result
    
    def _format_readiness_semantic(self, data: Dict[str, Any]) -> str:
        """Format readiness data semantically."""
        score = data.get("score", 0)
        
        result = f"# Readiness Report\n\n"
        result += f"**Date:** {data.get('day')}\n"
        result += f"**Score:** {score}/100\n\n"
        
        contributors = data.get("contributors", {})
        if contributors:
            result += "## Contributing Factors\n"
            for key, value in contributors.items():
                result += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        return result
    
    def _format_activity_semantic(self, data: Dict[str, Any]) -> str:
        """Format activity data semantically."""
        score = data.get("score", 0)

        result = f"# Activity Report\n\n"
        result += f"**Date:** {data.get('day')}\n"
        result += f"**Score:** {score}/100\n\n"
        result += f"- Steps: {data.get('steps', 0):,}\n"
        result += f"- Calories: {data.get('total_calories', 0)}\n"

        return result

    def _format_hrv_latest(
        self,
        readiness_data: Dict[str, Any],
        baseline_data: List[Dict[str, Any]]
    ) -> str:
        """Format latest HRV data with baseline comparison."""
        contributors = readiness_data.get("contributors", {})
        hrv_balance = contributors.get("hrv_balance")

        if hrv_balance is None:
            return "No HRV data available for today"

        # Calculate baseline
        baselines = self.baseline_manager.calculate_readiness_baselines(baseline_data)
        hrv_baseline = baselines.get("hrv_balance", {})

        # Interpret HRV
        hrv_interp = self.interpreter.interpret_hrv_balance(
            hrv_balance,
            hrv_baseline.get("mean")
        )

        result = f"# 💚 HRV Report\n\n"
        result += f"**Date:** {readiness_data.get('day')}\n"
        result += f"**HRV Balance:** {hrv_balance}/100\n"
        result += f"**Status:** {hrv_interp['emoji']} {hrv_interp['status']}\n\n"

        result += f"## Interpretation\n"
        result += f"- {hrv_interp['description']}\n"
        result += f"- **Meaning:** {hrv_interp['meaning']}\n"
        result += f"- **Implications:** {hrv_interp['implications']}\n\n"

        if 'baseline_status' in hrv_interp:
            result += f"## Baseline Comparison\n"
            result += f"- **30-day Average:** {hrv_baseline.get('mean', 0):.1f}\n"
            result += f"- **Status:** {hrv_interp['baseline_status']}\n"
            if 'deviation_pct' in hrv_interp:
                result += f"- **Deviation:** {hrv_interp['deviation_pct']:+.1f}%\n"
            result += f"- **Range:** {hrv_baseline.get('min', 0):.0f} - {hrv_baseline.get('max', 0):.0f}\n\n"

        # Add resting HR if available
        resting_hr = contributors.get("resting_heart_rate")
        if resting_hr:
            rhr_baseline = baselines.get("resting_heart_rate", {})
            result += f"## Resting Heart Rate\n"
            result += f"- **Current:** {resting_hr}/100 (contributor score)\n"
            if rhr_baseline.get("mean"):
                result += f"- **30-day Average:** {rhr_baseline['mean']:.1f}\n"
            result += "\n"

        return result

    def _format_hrv_trend(
        self,
        readiness_data: List[Dict[str, Any]],
        days: int
    ) -> str:
        """Format HRV trend over period."""
        hrv_values = []
        dates = []

        for record in readiness_data:
            contributors = record.get("contributors", {})
            hrv = contributors.get("hrv_balance")
            if hrv is not None:
                hrv_values.append(hrv)
                dates.append(record.get("day"))

        if not hrv_values:
            return f"No HRV data available for the last {days} days"

        # Calculate trend statistics
        import statistics
        avg_hrv = statistics.mean(hrv_values)
        std_hrv = statistics.stdev(hrv_values) if len(hrv_values) > 1 else 0
        min_hrv = min(hrv_values)
        max_hrv = max(hrv_values)

        # Determine trend direction
        if len(hrv_values) >= 3:
            recent_avg = statistics.mean(hrv_values[-3:])
            older_avg = statistics.mean(hrv_values[:len(hrv_values)//2])
            if recent_avg > older_avg + 5:
                trend = "Improving 📈"
            elif recent_avg < older_avg - 5:
                trend = "Declining 📉"
            else:
                trend = "Stable ↔️"
        else:
            trend = "Insufficient data"

        result = f"# 📈 HRV Trend Analysis ({days} days)\n\n"
        result += f"**Data Points:** {len(hrv_values)}\n"
        result += f"**Date Range:** {dates[0]} to {dates[-1]}\n\n"

        result += f"## Statistics\n"
        result += f"- **Average:** {avg_hrv:.1f}\n"
        result += f"- **Latest:** {hrv_values[-1]}\n"
        result += f"- **Range:** {min_hrv:.0f} - {max_hrv:.0f}\n"
        result += f"- **Std Dev:** {std_hrv:.1f}\n"
        result += f"- **Trend:** {trend}\n\n"

        # Interpret current state
        latest_hrv = hrv_values[-1]
        hrv_interp = self.interpreter.interpret_hrv_balance(latest_hrv, avg_hrv)

        result += f"## Current Status\n"
        result += f"{hrv_interp['emoji']} **{hrv_interp['status']}**\n"
        result += f"- {hrv_interp['description']}\n"
        result += f"- {hrv_interp['implications']}\n\n"

        # Check for consecutive patterns
        if len(hrv_values) >= 3:
            # Check for consecutive decline
            consecutive_decline = all(
                hrv_values[i] < hrv_values[i + 1]
                for i in range(min(3, len(hrv_values) - 1))
            )
            if consecutive_decline:
                result += f"## ⚠️ Pattern Detected\n"
                result += f"HRV has declined for {min(3, len(hrv_values))} consecutive days.\n"
                result += f"- **Recommendation:** Consider rest or reduced training load\n"
                result += f"- **Monitor for:** Overtraining, illness, stress accumulation\n\n"

        return result
    
    async def run(self):
        """Run the MCP server."""
        logger.info(f"Starting {self.config.mcp.server.name}...")
        
        async with self:
            if self.config.mcp.server.transport == "stdio":
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(
                        read_stream,
                        write_stream,
                        self.server.create_initialization_options()
                    )
            else:
                raise NotImplementedError("Only stdio transport is currently supported")


async def start_server(config_path: Optional[str] = None):
    """
    Start the Oura MCP server.
    
    Args:
        config_path: Optional path to config file
    """
    # Load config
    if config_path:
        os.environ["OURA_MCP_CONFIG"] = config_path
    
    config = get_config()
    
    # Setup logging
    setup_logging(config.logging)
    
    # Create and run server
    server = OuraMCPServer(config)
    await server.run()
