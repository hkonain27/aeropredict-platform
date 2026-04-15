import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  LabelList,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  Plane,
  Clock3,
  Search,
  MapPin,
  TrendingUp,
  AlertTriangle,
  CalendarRange,
  Activity,
  Filter,
  RefreshCcw,
  Building2,
} from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";
const MotionDiv = motion.div;
const pieColors = ["#0f2a5f", "#1d4ed8", "#38bdf8", "#7dd3fc", "#bae6fd"];

const statusStyles = {
  Low: "bg-sky-50 text-blue-950 border-sky-200",
  "Low Risk": "bg-sky-50 text-blue-950 border-sky-200",
  "Lower Delay Risk": "bg-sky-50 text-blue-950 border-sky-200",
  Medium: "bg-gray-100 text-blue-950 border-gray-300",
  Moderate: "bg-gray-100 text-blue-950 border-gray-300",
  "Elevated Delay Risk": "bg-gray-100 text-blue-950 border-gray-300",
  High: "bg-rose-50 text-rose-900 border-rose-200",
  "High Risk": "bg-rose-50 text-rose-900 border-rose-200",
  "High Delay Risk": "bg-rose-50 text-rose-900 border-rose-200",
  Critical: "bg-rose-50 text-rose-900 border-rose-200",
};

const riskThemes = {
  low: {
    panel: "border-sky-200 bg-white",
    accent: "bg-sky-50",
    badge: "bg-sky-50 text-blue-950 border-sky-200",
    title: "text-blue-950",
    progress: "[&_[data-slot=progress-indicator]]:bg-sky-500",
    bar: "#38bdf8",
  },
  medium: {
    panel: "border-gray-300 bg-white",
    accent: "bg-gray-50",
    badge: "bg-gray-100 text-blue-950 border-gray-300",
    title: "text-blue-950",
    progress: "[&_[data-slot=progress-indicator]]:bg-gray-500",
    bar: "#64748b",
  },
  high: {
    panel: "border-rose-200 bg-rose-50",
    accent: "bg-rose-50",
    badge: "bg-rose-50 text-rose-900 border-rose-200",
    title: "text-rose-900",
    progress: "[&_[data-slot=progress-indicator]]:bg-rose-400",
    bar: "#fb7185",
  },
};

const MONTH_LABELS = {
  1: "Jan",
  2: "Feb",
  3: "Mar",
  4: "Apr",
  5: "May",
  6: "Jun",
  7: "Jul",
  8: "Aug",
  9: "Sep",
  10: "Oct",
  11: "Nov",
  12: "Dec",
};

const EMPTY_FORM = {
  carrier: "",
  airport: "",
  month: "",
};

const EMPTY_DASHBOARD_DATA = {
  summaryCards: [],
  monthlyDelayData: [],
  airportRiskData: [],
  causeBreakdown: [],
  forecastData: [],
  recentFlights: [],
  suggestionScenarios: [],
};

const normalizeDashboardData = (payload = {}) => ({
  summaryCards: Array.isArray(payload.summaryCards) ? payload.summaryCards : [],
  monthlyDelayData: Array.isArray(payload.monthlyDelayData) ? payload.monthlyDelayData : [],
  airportRiskData: Array.isArray(payload.airportRiskData) ? payload.airportRiskData : [],
  causeBreakdown: Array.isArray(payload.causeBreakdown) ? payload.causeBreakdown : [],
  forecastData: Array.isArray(payload.forecastData) ? payload.forecastData : [],
  recentFlights: Array.isArray(payload.recentFlights) ? payload.recentFlights : [],
  suggestionScenarios: Array.isArray(payload.suggestionScenarios) ? payload.suggestionScenarios : [],
});

const formatCount = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  return Number(value).toLocaleString();
};

const monthName = (value) => MONTH_LABELS[Number(value)] || value;

const toPercentNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  const number = Number(value);
  return number <= 1 ? number * 100 : number;
};

const formatPercentValue = (value) => {
  const percent = toPercentNumber(value);
  return percent === null ? "n/a" : `${percent.toFixed(1)}%`;
};

const frequencyText = (value, noun = "flights") => {
  const percent = toPercentNumber(value);
  if (!percent || percent <= 0) return null;
  const every = Math.max(1, Math.round(100 / percent));
  return `about 1 in ${every} ${noun}`;
};

const contextualPercent = (value, noun = "flights") => {
  const percent = formatPercentValue(value);
  const frequency = frequencyText(value, noun);
  return frequency ? `${percent} (${frequency})` : percent;
};

const delayImpact = (minutes) => {
  if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) return "impact unknown";
  const value = Number(minutes);
  if (value < 10) return "minor impact";
  if (value < 25) return "moderate impact";
  return "major impact";
};

const formatDelayMinutes = (minutes) => {
  if (minutes === null || minutes === undefined || Number.isNaN(Number(minutes))) return "n/a";
  return `${Number(minutes).toFixed(1)} min (${delayImpact(minutes)})`;
};

const comparePercent = (value, baseline) => {
  const percent = toPercentNumber(value);
  const baselinePercent = toPercentNumber(baseline);
  if (percent === null || baselinePercent === null) return null;

  const delta = percent - baselinePercent;
  const direction = Math.abs(delta) < 1
    ? "about average"
    : delta > 0
      ? "higher than average"
      : "better than average";
  const amount = Math.abs(delta) < 1 ? "" : ` by ${Math.abs(delta).toFixed(1)} pts`;
  return `${percent.toFixed(1)}% vs ${baselinePercent.toFixed(1)}% typical -> ${direction}${amount}`;
};

const riskLevelKey = (label = "") => {
  if (String(label).toLowerCase().includes("high")) return "high";
  if (String(label).toLowerCase().includes("elevated") || String(label).toLowerCase().includes("moderate")) return "medium";
  return "low";
};

const isWithinDateRange = (createdAt, dateRange) => {
  if (!createdAt) return true;
  const createdTime = new Date(createdAt).getTime();
  if (Number.isNaN(createdTime)) return true;

  const now = Date.now();
  const hours = {
    "24h": 24,
    "7days": 24 * 7,
    "30days": 24 * 30,
    all: Number.POSITIVE_INFINITY,
  };

  return now - createdTime <= hours[dateRange] * 60 * 60 * 1000;
};

const validateField = (field, value) => {
  switch (field) {
    case "carrier":
      if (!String(value).trim()) return "Required";
      if (!/^[A-Z0-9]{2,3}$/i.test(String(value).trim())) return "Use a carrier code like AA or DL";
      return null;
    case "airport":
      if (!String(value).trim()) return "Required";
      if (!/^[A-Z]{3}$/i.test(String(value).trim())) return "Use a 3-letter airport code like CLT";
      return null;
    case "month": {
      const n = Number(value);
      if (value === "") return "Required";
      if (!Number.isInteger(n)) return "Must be a whole number";
      if (n < 1 || n > 12) return "Must be between 1 and 12";
      return null;
    }
    default:
      return null;
  }
};

function EmptyPanel({ title, description }) {
  return (
    <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-sky-200 bg-sky-50 p-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-medium text-blue-950">{title}</p>
        <p className="mt-2 text-sm text-blue-700">{description}</p>
      </div>
    </div>
  );
}

function prettyCauseName(name) {
  switch (name) {
    case "Carrier":
      return "Airline operations";
    case "Weather":
      return "Weather disruptions";
    case "NAS":
      return "Air traffic system";
    case "Security":
      return "Security delays";
    case "Late Aircraft":
      return "Late inbound aircraft";
    default:
      return name;
  }
}

export default function App() {
  const [data, setData] = useState(EMPTY_DASHBOARD_DATA);
  const [loading, setLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState(null);
  const [airportFilter, setAirportFilter] = useState("all");
  const [dateRange, setDateRange] = useState("all");
  const [search, setSearch] = useState("");

  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [comparisonBaseline, setComparisonBaseline] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
  const [history, setHistory] = useState([]);

  const fetchDashboardData = async () => {
    try {
      setDashboardError(null);
      const response = await fetch(`${API_BASE}/api/dashboard-data`);
      if (!response.ok) throw new Error("Failed to load dashboard data");
      const json = await response.json();
      setData(normalizeDashboardData(json));
    } catch (error) {
      console.error(error);
      setDashboardError("Could not load dashboard data from the backend.");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/predictions`);
      if (!res.ok) throw new Error("Failed to load prediction history");
      const json = await res.json();
      if (json.status === "success" && Array.isArray(json.predictions)) setHistory(json.predictions);
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchHistory();
  }, []);

  const handleFormChange = (field, value) => {
    const nextValue = ["carrier", "airport"].includes(field) ? value.toUpperCase() : value;
    setForm((prev) => ({ ...prev, [field]: nextValue }));
    setFieldErrors((prev) => ({ ...prev, [field]: null }));
  };

  const handleBlur = (field) => {
    setFieldErrors((prev) => ({ ...prev, [field]: validateField(field, form[field]) }));
  };

  const handlePredict = async () => {
    setPredicting(true);
    setPredictionError(null);

    const errors = {};
    Object.keys(form).forEach((field) => {
      const err = validateField(field, form[field]);
      if (err) errors[field] = err;
    });

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setPredictionError("Please fix the highlighted fields before running a prediction.");
      setPredicting(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          carrier: form.carrier,
          airport: form.airport,
          month: parseInt(form.month, 10),
        }),
      });

      const json = await response.json();

      if (!response.ok || json.status === "error") {
        setPredictionError(json.message || "Prediction failed.");
      } else {
        setComparisonBaseline(predictionResult);
        setPredictionResult(json);
        fetchHistory();
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
      setPredictionError("Could not connect to the backend prediction endpoint.");
    } finally {
      setPredicting(false);
    }
  };

  const filteredFlights = useMemo(() => {
    return data.recentFlights.filter((flight) => {
      const matchesAirport = airportFilter === "all" || flight.airport === airportFilter;
      const q = search.toLowerCase();
      const matchesSearch =
        flight.id.toLowerCase().includes(q) ||
        flight.route.toLowerCase().includes(q) ||
        flight.airline.toLowerCase().includes(q) ||
        flight.airport.toLowerCase().includes(q);
      const matchesDateRange = isWithinDateRange(flight.createdAt, dateRange);
      return matchesAirport && matchesSearch && matchesDateRange;
    });
  }, [airportFilter, search, dateRange, data.recentFlights]);

  const airportOptions = useMemo(() => {
    return [...new Set(data.recentFlights.map((flight) => flight.airport))].sort();
  }, [data.recentFlights]);

  const topAirportRisk = data.airportRiskData?.[0];
  const normalizedCauseBreakdown = useMemo(() => {
    if (!data.causeBreakdown?.length) return [];
    const total = data.causeBreakdown.reduce((sum, item) => sum + item.value, 0);
    if (!total) return data.causeBreakdown;
    return data.causeBreakdown.map((item) => ({
      ...item,
      value: Number(((item.value / total) * 100).toFixed(1)),
    }));
  }, [data.causeBreakdown]);

  const topCause = useMemo(() => {
    if (!normalizedCauseBreakdown.length) return null;
    return [...normalizedCauseBreakdown].sort((a, b) => b.value - a.value)[0];
  }, [normalizedCauseBreakdown]);

  const highestDelayMonths = useMemo(() => {
    return [...data.monthlyDelayData]
      .sort((a, b) => Number(b.avgDelay) - Number(a.avgDelay))
      .slice(0, 3)
      .map((item) => String(item.month));
  }, [data.monthlyDelayData]);

  const formExamples = useMemo(() => {
    if (data.suggestionScenarios.length > 0) return data.suggestionScenarios;

    const months = highestDelayMonths.length > 0 ? highestDelayMonths : ["12", "7", "1"];
    return [
      { risk: "Low", label: "Lower historical delay pattern", carrier: "AA", airport: "CLT", month: months[0], delayRate: null },
      { risk: "Medium", label: "Worth watching", carrier: "WN", airport: "DEN", month: months[1] || months[0], delayRate: null },
      { risk: "High", label: "Higher historical delay pattern", carrier: "UA", airport: "ORD", month: months[2] || months[0], delayRate: null },
    ];
  }, [data.suggestionScenarios, highestDelayMonths]);

  const probabilityDelta = predictionResult && comparisonBaseline
    ? (predictionResult.delay_probability - comparisonBaseline.delay_probability) * 100
    : null;
  const currentAnalysis = predictionResult?.analysis;
  const historicalContext = currentAnalysis?.historical?.context_used;
  const monthBaseline = currentAnalysis?.historical?.month_baseline;
  const causeMix = historicalContext?.cause_breakdown || [];
  const liveWeather = predictionResult?.live_weather;
  const weatherRisk = predictionResult?.weather_risk;
  const historicalWeather = predictionResult?.historical_weather;
  const historicalWeatherRisk = predictionResult?.historical_weather_risk;
  const flight2024Context = predictionResult?.flight_2024_context;
  const flight2024Summary = flight2024Context?.summary;
  const flight2024Risk = predictionResult?.flight_2024_risk;
  const rawModel = predictionResult?.raw_model;
  const finalRiskScore = predictionResult?.final_risk_score;
  const finalRiskComponents = predictionResult?.final_risk_components || [];
  const componentLabelMap = {
    model: "Model (main driver)",
    historical: "Historical (support)",
    flight_2024: "2024 flights",
    historical_weather: "Weather history",
  };
  const riskContributionData = finalRiskComponents.map((component) => ({
    name: componentLabelMap[component.key] || component.label,
    contribution: component.contribution_percent,
    weight: component.weight_percent,
    score: Math.round(component.score * 1000) / 10,
  }));
  const displayRiskLabel = predictionResult?.final_risk_label || predictionResult?.prediction_label || currentAnalysis?.risk_label;
  const riskTheme = riskThemes[riskLevelKey(displayRiskLabel)];
  const weatherRiskStyles = {
    High: "bg-rose-50 text-rose-900 border-rose-200",
    Moderate: "bg-gray-100 text-blue-950 border-gray-300",
    Low: "bg-sky-50 text-blue-950 border-sky-200",
    Unknown: "bg-white text-blue-900 border-sky-200",
  };
  const weatherRiskBadgeClass = weatherRiskStyles[weatherRisk?.level] || weatherRiskStyles.Unknown;
  const historicalWeatherRiskBadgeClass = weatherRiskStyles[historicalWeatherRisk?.level] || weatherRiskStyles.Unknown;
  const historicalDelayComparison = comparePercent(historicalContext?.delay_rate, monthBaseline?.delay_rate);
  const recentDelayComparison = comparePercent(flight2024Summary?.delay_rate, historicalContext?.delay_rate);
  const sortedCauseMix = [...causeMix]
    .filter((item) => item.share > 0)
    .sort((a, b) => b.share - a.share);
  const primaryCause = sortedCauseMix[0];
  const secondaryCause = sortedCauseMix[1];
  const keyTakeaway = predictionResult
    ? `${displayRiskLabel || "Delay risk"} for ${predictionResult.input.carrier} at ${predictionResult.input.airport} in ${monthName(predictionResult.input.month)}. ${
        primaryCause
          ? `The biggest historical driver is ${prettyCauseName(primaryCause.name).toLowerCase()} (${primaryCause.share}%).`
          : "The score is based on the model, recent flights, historical delay trends, and historical weather."
      }`
    : null;

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-sky-50">
        <RefreshCcw className="h-6 w-6 animate-spin text-blue-700" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-sky-50 text-blue-950">
      <div className="mx-auto max-w-7xl p-4 md:p-8">
        <MotionDiv
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge className="rounded-full bg-blue-100 px-3 py-1 text-blue-700 hover:bg-blue-100">
                AeroPredict
              </Badge>
              <Badge variant="outline" className="rounded-full border-sky-200 bg-white text-blue-900">
                arrival delay risk
              </Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">AeroPredict</h1>
            <p className="mt-2 max-w-3xl text-sm text-blue-900 md:text-base">
              Predict flight delay risk, explore saved delay patterns, and compare scenarios in one place.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" className="rounded-2xl" onClick={() => { setLoading(true); fetchDashboardData(); fetchHistory(); }}>
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
          </div>
        </MotionDiv>

        {dashboardError && (
          <Alert className="mb-6 rounded-2xl border-sky-300 bg-white">
            <AlertTriangle className="h-4 w-4 text-blue-950" />
            <AlertDescription className="text-blue-950">{dashboardError}</AlertDescription>
          </Alert>
        )}

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.summaryCards.map((card, index) => {
            const iconMap = { Plane, Clock3, Building2, TrendingUp, MapPin };
            const Icon = iconMap[card.icon] || Plane;
            return (
              <MotionDiv
                key={card.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: index * 0.06 }}
              >
                <Card className="rounded-2xl border-none shadow-sm">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-blue-700">{card.title}</p>
                        <h2 className="mt-2 text-3xl font-semibold">{card.value}</h2>
                        <p className="mt-2 text-sm text-blue-700">
                          <span className="font-medium text-blue-900">{card.change}</span>
                        </p>
                      </div>
                      <div className="rounded-2xl bg-sky-100 p-3">
                        <Icon className="h-5 w-5" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </MotionDiv>
            );
          })}
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 xl:grid-cols-12">
          <Card className="rounded-2xl border-none shadow-sm xl:col-span-8">
            <CardHeader>
              <CardTitle>Monthly Delay Rate Trend</CardTitle>
              <CardDescription>Average share of arrivals delayed by 15+ minutes across all airport-airline combinations</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {data.monthlyDelayData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.monthlyDelayData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#bae6fd" />
                    <XAxis dataKey="monthLabel" tick={{ fill: "#0f2a5f" }} />
                    <YAxis tick={{ fill: "#0f2a5f" }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip
                      labelFormatter={(label) => `Month: ${label}`}
                      formatter={(value) => [`${value}%`, "Historical delay rate"]}
                    />
                    <Bar dataKey="avgDelay" fill="#1d4ed8" radius={[8, 8, 0, 0]} name="Historical delay rate" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyPanel
                  title="No monthly trend data yet"
                  description="The backend dashboard endpoint needs to return monthly delay data for this panel to populate."
                />
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
            <CardHeader>
              <CardTitle>Delay Cause Mix</CardTitle>
              <CardDescription>Share of delay minutes attributed to each operational cause</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {normalizedCauseBreakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={normalizedCauseBreakdown} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={3}>
                      {normalizedCauseBreakdown.map((entry, index) => (
                        <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <EmptyPanel
                  title="No cause data yet"
                  description="Cause totals will appear here once the dashboard dataset loads successfully."
                />
              )}
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="predictions" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-3 rounded-2xl bg-white p-1 shadow-sm md:w-[420px]">
            <TabsTrigger value="overview" className="rounded-xl">Overview</TabsTrigger>
            <TabsTrigger value="predictions" className="rounded-xl">Predictions</TabsTrigger>
            <TabsTrigger value="history" className="rounded-xl">History</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-7">
                <CardHeader>
                  <CardTitle>Highest-Risk Airports</CardTitle>
                  <CardDescription>Average delay rate by airport across the processed BTS dataset</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                  {data.airportRiskData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.airportRiskData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="airport" />
                        <YAxis />
                        <Tooltip formatter={(value) => `${value}%`} />
                        <Bar dataKey="risk" radius={[8, 8, 0, 0]} fill="#2563eb" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyPanel
                      title="No airport risk data yet"
                      description="Airport rankings will appear once the dashboard dataset is available."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-5">
                <CardHeader>
                  <CardTitle>Operational Insights</CardTitle>
                  <CardDescription>Real explanations grounded in the delay-cause dataset</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="rounded-2xl bg-sky-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><MapPin className="h-4 w-4" /> Highest average risk</div>
                    <p className="text-sm text-blue-900">
                      {topAirportRisk
                        ? `${topAirportRisk.airport} currently has the highest average arrival delay risk in the dashboard data at ${topAirportRisk.risk}%.`
                        : "Airport-level risk insights will appear here once dashboard data is loaded."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-sky-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Activity className="h-4 w-4" /> Strongest system-wide cause</div>
                    <p className="text-sm text-blue-900">
                      {topCause
                        ? `${prettyCauseName(topCause.name)} is currently the largest contributor to total delay minutes, accounting for about ${topCause.value}% of the overall delay burden.`
                        : "Cause-level insights will appear here when cause totals are available."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-sky-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><TrendingUp className="h-4 w-4" /> What this model predicts</div>
                    <p className="text-sm text-blue-900">
                      This model predicts whether an airport-airline-month combination is likely to be delay-heavy, using carrier, airport, month, and arriving flight volume.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="predictions">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-7">
                <CardHeader>
                  <CardTitle>Search Delay Risk</CardTitle>
                  <CardDescription>Run the main prediction and see the weighted evidence behind the final risk</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    {formExamples.map((example) => {
                      const exampleTone = riskThemes[riskLevelKey(example.risk)];
                      const delayText = example.delayRate !== null && example.delayRate !== undefined
                        ? `${riskLevelKey(example.risk) === "low" ? "Only " : ""}~${example.delayRate}% delayed (${frequencyText(example.delayRate) || "historical pattern"})`
                        : example.label;
                      return (
                        <Button
                          key={`${example.carrier}-${example.airport}-${example.month}`}
                          variant="outline"
                          className={`h-auto justify-start rounded-xl p-3 text-left text-sm hover:bg-white ${exampleTone.badge}`}
                          onClick={() => {
                            setForm({
                              carrier: example.carrier,
                              airport: example.airport,
                              month: String(example.month),
                            });
                            setFieldErrors({});
                            setPredictionError(null);
                          }}
                        >
                          <span className="flex flex-col gap-1">
                          <span className="font-semibold">{example.risk || "Example"} risk</span>
                          <span>{example.carrier} @ {example.airport} in {monthName(example.month)}</span>
                          <span className="text-blue-700">
                            {delayText}
                          </span>
                        </span>
                        </Button>
                      );
                    })}
                  </div>

                  <div>
                    <Input
                      placeholder="Carrier code (e.g. AA)"
                      value={form.carrier}
                      onChange={(e) => handleFormChange("carrier", e.target.value)}
                      onBlur={() => handleBlur("carrier")}
                      className={`rounded-xl ${fieldErrors.carrier ? "border-blue-950" : ""}`}
                    />
                    {fieldErrors.carrier && <p className="mt-1 text-xs text-blue-950">{fieldErrors.carrier}</p>}
                  </div>

                  <div>
                    <Input
                      placeholder="Airport code (e.g. CLT)"
                      value={form.airport}
                      onChange={(e) => handleFormChange("airport", e.target.value)}
                      onBlur={() => handleBlur("airport")}
                      className={`rounded-xl ${fieldErrors.airport ? "border-blue-950" : ""}`}
                    />
                    {fieldErrors.airport && <p className="mt-1 text-xs text-blue-950">{fieldErrors.airport}</p>}
                  </div>

                  <div>
                    <Select value={form.month} onValueChange={(value) => handleFormChange("month", value)}>
                      <SelectTrigger className={`rounded-xl ${fieldErrors.month ? "border-blue-950" : ""}`}>
                        <SelectValue placeholder="Select month" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(MONTH_LABELS).map(([value, label]) => (
                          <SelectItem key={value} value={String(value)}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {fieldErrors.month && <p className="mt-1 text-xs text-blue-950">{fieldErrors.month}</p>}
                  </div>

                  <div className="flex gap-2">
                    <Button className="flex-1 rounded-xl" onClick={handlePredict} disabled={predicting}>
                      {predicting ? "Searching..." : "Search Delay Risk"}
                    </Button>
                    <Button
                      variant="outline"
                      className="rounded-xl"
                      onClick={() => {
                        setForm(EMPTY_FORM);
                        setFieldErrors({});
                        setPredictionResult(null);
                        setComparisonBaseline(null);
                        setPredictionError(null);
                      }}
                    >
                      Reset
                    </Button>
                  </div>

                  {predictionError && (
                    <Alert className="rounded-xl border-sky-300 bg-white">
                      <AlertTriangle className="h-4 w-4 text-blue-950" />
                      <AlertDescription className="text-blue-950">{predictionError}</AlertDescription>
                    </Alert>
                  )}

                  {predictionResult && (
                    <div className={`rounded-xl border p-5 ${riskTheme.panel}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={`text-xl font-semibold ${riskTheme.title}`}>
                            {displayRiskLabel}
                          </p>
                          <p className="mt-1 text-sm text-blue-900">
                            {predictionResult.input.carrier} at {predictionResult.input.airport} in {monthName(predictionResult.input.month)}.
                          </p>
                        </div>
                        <Badge variant="outline" className={`rounded-full border px-3 py-1 text-sm ${riskTheme.badge}`}>
                          {finalRiskScore !== undefined ? `${(finalRiskScore * 100).toFixed(1)}%` : `${(predictionResult.delay_probability * 100).toFixed(1)}%`}
                        </Badge>
                      </div>

                      <Progress value={(finalRiskScore ?? predictionResult.delay_probability) * 100} className={`mt-4 h-3 bg-white ${riskTheme.progress}`} />

                      {keyTakeaway && (
                        <div className={`mt-4 rounded-xl border border-sky-200 p-4 ${riskTheme.accent}`}>
                          <p className="text-sm font-semibold text-blue-950">Key Takeaway</p>
                          <p className="mt-1 text-sm text-blue-900">{keyTakeaway}</p>
                        </div>
                      )}

                      <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                        <div className="rounded-xl border border-sky-200 bg-white p-3">
                          <p className="text-blue-700">Raw model</p>
                          <p className="mt-1 font-semibold text-blue-950">
                            {rawModel ? `${(rawModel.delay_probability * 100).toFixed(1)}%` : "n/a"}
                          </p>
                          <p className="mt-1 text-sm text-blue-900">{rawModel?.prediction_label || "Model result unavailable"}</p>
                        </div>
                        <div className="rounded-xl border border-sky-200 bg-white p-3">
                          <p className="text-blue-700">2024 evidence</p>
                          <p className="mt-1 font-semibold text-blue-950">
                            {flight2024Summary ? contextualPercent(flight2024Summary.delay_rate) : "n/a"}
                          </p>
                          <p className="mt-1 text-sm text-blue-900">{recentDelayComparison || flight2024Risk?.level || "Recent context unavailable"}</p>
                        </div>
                        <div className="rounded-xl border border-sky-200 bg-white p-3">
                          <p className="text-blue-700">Historical weather</p>
                          <p className="mt-1 font-semibold text-blue-950">
                            {historicalWeather?.available ? (historicalWeatherRisk?.level || "Reported") : "Unavailable"}
                          </p>
                          <p className="mt-1 text-sm text-blue-900">
                            {historicalWeather?.available
                              ? `${formatPercentValue(historicalWeather.precipitation_rate)} precipitation observations`
                              : "No weather context available"}
                          </p>
                        </div>
                      </div>
                      {riskContributionData.length > 0 && (
                        <div className="mt-4 rounded-xl border border-sky-200 bg-white p-4">
                          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-blue-950">What's driving this prediction</p>
                              <p className="mt-1 text-sm text-blue-900">Shows how each factor contributed to final risk.</p>
                            </div>
                            <Badge variant="outline" className="w-fit rounded-full border-sky-200 bg-sky-50 text-blue-900">
                              month analysis
                            </Badge>
                          </div>
                          <div className="h-[210px]">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={riskContributionData} layout="vertical" margin={{ left: 20, right: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" domain={[0, 50]} tickFormatter={(value) => `${value}%`} />
                                <YAxis type="category" dataKey="name" width={116} tick={{ fontSize: 12 }} />
                                <Tooltip
                                  formatter={(value, name, props) => {
                                    if (name === "contribution") return [`${value}%`, "Final-score contribution"];
                                    return [`${props.payload.weight}%`, "Effective weight"];
                                  }}
                                />
                                <Bar dataKey="contribution" fill={riskTheme.bar} radius={[0, 8, 8, 0]}>
                                  <LabelList dataKey="contribution" position="right" formatter={(value) => `${value}%`} />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}

                      {flight2024Context && (
                        <div className="mt-4 space-y-3 rounded-xl border border-sky-200 bg-white p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-blue-950">Recent (2024) flight behavior</p>
                              <p className="mt-1 text-sm text-blue-900">Recent flights show whether this route has been behaving better or worse than its longer-term pattern.</p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${weatherRiskStyles[flight2024Risk?.level] || weatherRiskStyles.Unknown}`}>
                              {flight2024Risk?.level || "Unknown"}
                            </Badge>
                          </div>

                          {flight2024Context.available && flight2024Summary ? (
                            <>
                              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Flights</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {formatCount(flight2024Summary.flights)}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Delay rate</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {contextualPercent(flight2024Summary.delay_rate)}
                                  </p>
                                  {recentDelayComparison && <p className="mt-1 text-sm text-blue-900">{recentDelayComparison}</p>}
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Cancelled</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {contextualPercent(flight2024Summary.cancellation_rate, "flights")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Avg delay</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {formatDelayMinutes(flight2024Summary.avg_arrival_delay_minutes)}
                                  </p>
                                </div>
                              </div>

                              {flight2024Risk?.drivers?.length > 0 && (
                                <ul className="space-y-1 text-sm text-blue-900">
                                  {flight2024Risk.drivers.slice(0, 2).map((driver) => (
                                    <li key={driver}>{driver}</li>
                                  ))}
                                </ul>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-blue-900">
                              {flight2024Context.message || "No 2024 flight evidence is available for this airport-airline-month combination."}
                            </p>
                          )}
                        </div>
                      )}

                      {(historicalWeather || historicalWeatherRisk) && (
                        <div className="mt-4 space-y-3 rounded-xl border border-sky-200 bg-white p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-blue-950">Historical weather pattern</p>
                              <p className="mt-1 text-sm text-blue-900">
                                {historicalWeather?.available
                                  ? `${monthName(predictionResult.input.month)} ${historicalWeather.reference_year} observations at ${historicalWeather.station}.`
                                  : historicalWeather?.message || "Historical airport weather is unavailable for this airport and month."}
                              </p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${historicalWeatherRiskBadgeClass}`}>
                              {historicalWeatherRisk?.level || "Unknown"}
                            </Badge>
                          </div>

                          {historicalWeather?.available ? (
                            <>
                              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Observations</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {formatCount(historicalWeather.observations)}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Low visibility</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {contextualPercent(historicalWeather.low_visibility_rate, "observations")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Gusty wind</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {contextualPercent(historicalWeather.gusty_wind_rate, "observations")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-sky-50 p-3">
                                  <p className="text-blue-700">Precipitation</p>
                                  <p className="mt-1 text-lg font-semibold text-blue-950">
                                    {contextualPercent(historicalWeather.precipitation_rate, "observations")}
                                  </p>
                                </div>
                              </div>

                              {historicalWeatherRisk?.drivers?.length > 0 && (
                                <ul className="space-y-1 text-sm text-blue-900">
                                  {historicalWeatherRisk.drivers.slice(0, 2).map((driver) => (
                                    <li key={driver}>{driver}</li>
                                  ))}
                                </ul>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-blue-900">
                              {historicalWeatherRisk?.drivers?.[0] || "Historical airport weather is unavailable."}
                            </p>
                          )}
                        </div>
                      )}

                      {currentAnalysis && (
                        <div className="mt-4 space-y-4 rounded-xl border border-sky-200 bg-white p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-blue-950">Long-term delay trends</p>
                              <p className="mt-1 text-sm text-blue-900">This compares the selected airline and airport against the typical month pattern.</p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${statusStyles[currentAnalysis.risk_label] || statusStyles.Moderate}`}>
                              {currentAnalysis.risk_label}
                            </Badge>
                          </div>

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div className="rounded-xl bg-sky-50 p-3">
                              <p className="text-blue-700">Historical delay rate</p>
                              <p className="mt-1 text-xl font-semibold text-blue-950">
                                {contextualPercent(historicalContext?.delay_rate)}
                              </p>
                              {historicalDelayComparison && <p className="mt-1 text-sm text-blue-900">{historicalDelayComparison}</p>}
                            </div>
                            <div className="rounded-xl bg-sky-50 p-3">
                              <p className="text-blue-700">Month baseline</p>
                              <p className="mt-1 text-xl font-semibold text-blue-950">
                                {contextualPercent(monthBaseline?.delay_rate)}
                              </p>
                            </div>
                            <div className="rounded-xl bg-sky-50 p-3">
                              <p className="text-blue-700">Exact matches</p>
                              <p className="mt-1 text-xl font-semibold text-blue-950">
                                {currentAnalysis.availability.exact_matches}
                              </p>
                            </div>
                            <div className="rounded-xl bg-sky-50 p-3">
                              <p className="text-blue-700">Average delay minutes</p>
                              <p className="mt-1 text-xl font-semibold text-blue-950">
                                {formatDelayMinutes(historicalContext?.avg_delay_minutes_per_delayed_arrival)}
                              </p>
                            </div>
                          </div>

                          {causeMix.length > 0 && (
                            <div className="space-y-3">
                              <p className="text-sm font-medium text-blue-950">
                                Primary cause: {prettyCauseName(primaryCause.name)} ({primaryCause.share}%)
                              </p>
                              {secondaryCause && (
                                <p className="text-sm text-blue-900">
                                  Secondary: {prettyCauseName(secondaryCause.name)} ({secondaryCause.share}%)
                                </p>
                              )}
                              {causeMix
                                .filter((item) => item.share > 0)
                                .sort((a, b) => b.share - a.share)
                                .slice(0, 4)
                                .map((item) => (
                                  <div key={item.name}>
                                    <div className="mb-1 flex justify-between text-xs text-blue-900">
                                      <span>{item.name}</span>
                                      <span>{item.share}%</span>
                                    </div>
                                    <div className="h-1.5 w-full rounded-full bg-sky-200">
                                      <div className="h-1.5 rounded-full bg-blue-950" style={{ width: `${item.share}%` }} />
                                    </div>
                                  </div>
                                ))}
                            </div>
                          )}
                        </div>
                      )}

                      {(liveWeather || weatherRisk) && (
                        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-4">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-blue-950">Live current conditions</p>
                              <p className="mt-1 text-sm text-blue-900">
                                This is current weather, not for the selected month, and is not used in the {monthName(predictionResult.input.month)} score.
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-2 text-sm">
                              <Badge variant="outline" className={`rounded-full border ${weatherRiskBadgeClass}`}>
                                {liveWeather?.available ? (liveWeather.flight_category || "Reported") : "Unavailable"}
                              </Badge>
                              {liveWeather?.available && (
                                <>
                                  <Badge variant="outline" className="rounded-full border-sky-200 bg-white text-blue-900">
                                    {liveWeather.visibility_miles ?? "n/a"} mi
                                  </Badge>
                                  <Badge variant="outline" className="rounded-full border-sky-200 bg-white text-blue-900">
                                    {liveWeather.wind_speed_kt ?? "n/a"} kt wind
                                  </Badge>
                                </>
                              )}
                            </div>
                          </div>
                          {!liveWeather?.available && (
                            <p className="mt-3 text-sm text-blue-900">
                              {liveWeather?.message || "Live weather is not currently available for this airport."}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {predictionResult && comparisonBaseline && (
                    <div className="rounded-xl border border-sky-200 bg-white p-4">
                      <p className="text-sm font-medium text-blue-950">Scenario Comparison</p>
                      <p className="mt-1 text-sm text-blue-900">
                        Compared with your previous prediction, delay risk
                        <span className={`ml-1 font-medium ${probabilityDelta >= 0 ? "text-blue-950" : "text-sky-600"}`}>
                          {probabilityDelta >= 0 ? " increased " : " decreased "}
                          by {Math.abs(probabilityDelta).toFixed(1)} percentage points
                        </span>
                        .
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div className="rounded-xl bg-sky-50 p-3">
                          <p className="text-blue-700">Previous</p>
                          <p className="mt-1 font-medium">{comparisonBaseline.input.carrier} @ {comparisonBaseline.input.airport}</p>
                          <p className="text-blue-900">{(comparisonBaseline.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                        <div className="rounded-xl bg-sky-50 p-3">
                          <p className="text-blue-700">Current</p>
                          <p className="mt-1 font-medium">{predictionResult.input.carrier} @ {predictionResult.input.airport}</p>
                          <p className="text-blue-900">{(predictionResult.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-5">
                <CardHeader>
                  <CardTitle>Airline Risk Comparison</CardTitle>
                  <CardDescription>Highest airline-level delay rates from the dashboard dataset</CardDescription>
                </CardHeader>
                <CardContent className="h-[320px]">
                  {data.forecastData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.forecastData} layout="vertical" margin={{ left: 28, right: 24 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#bae6fd" />
                        <XAxis type="number" tick={{ fill: "#0f2a5f" }} tickFormatter={(value) => `${value}%`} />
                        <YAxis
                          type="category"
                          dataKey="carrierName"
                          width={150}
                          interval={0}
                          tick={{ fill: "#0f2a5f", fontSize: 12 }}
                        />
                        <Tooltip
                          formatter={(value) => [`${value}%`, "Airline delay rate"]}
                          labelFormatter={(label, items) => {
                            const carrier = items?.[0]?.payload?.carrier;
                            return carrier ? `${label} (${carrier})` : label;
                          }}
                        />
                        <Bar dataKey="actual" fill="#0f2a5f" radius={[8, 8, 0, 0]} name="Carrier delay rate" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyPanel
                      title="No carrier comparison yet"
                      description="Carrier-level trend data will appear here when the backend dashboard route is wired up."
                    />
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="history">
            <div className="grid grid-cols-1 gap-4">
              <Card className="rounded-2xl border-none shadow-sm">
                <CardHeader>
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <CardTitle>Prediction History</CardTitle>
                      <CardDescription>Saved airport-airline risk predictions from your running app</CardDescription>
                    </div>
                    <div className="grid w-full gap-3 md:grid-cols-2 xl:grid-cols-3 lg:w-auto">
                      <div className="relative min-w-[220px]">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-sky-500" />
                        <Input
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder="Search carrier, airport, record"
                          className="rounded-2xl pl-10"
                        />
                      </div>
                      <Select value={airportFilter} onValueChange={setAirportFilter}>
                        <SelectTrigger className="rounded-2xl"><SelectValue placeholder="Airport" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Airports</SelectItem>
                          {airportOptions.map((airport) => (
                            <SelectItem key={airport} value={airport}>{airport}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={dateRange} onValueChange={setDateRange}>
                        <SelectTrigger className="rounded-2xl">
                          <CalendarRange className="mr-2 h-4 w-4" />
                          <SelectValue placeholder="Date range" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All time</SelectItem>
                          <SelectItem value="24h">Last 24 Hours</SelectItem>
                          <SelectItem value="7days">Last 7 Days</SelectItem>
                          <SelectItem value="30days">Last 30 Days</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 flex items-center gap-2 text-sm text-blue-700">
                    <Filter className="h-4 w-4" /> Showing {filteredFlights.length} saved records
                  </div>
                  {filteredFlights.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[820px] border-separate border-spacing-y-3">
                        <thead>
                          <tr className="text-left text-sm text-blue-700">
                            <th className="px-4">Record</th>
                            <th className="px-4">Scenario</th>
                            <th className="px-4">Carrier</th>
                            <th className="px-4">Month</th>
                            <th className="px-4">Delay Probability</th>
                            <th className="px-4">Confidence</th>
                            <th className="px-4">Risk</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredFlights.map((flight) => (
                            <tr key={flight.id} className="bg-sky-50 text-sm text-blue-950">
                              <td className="rounded-l-2xl px-4 py-4 font-semibold">{flight.id}</td>
                              <td className="px-4 py-4">{flight.route}</td>
                              <td className="px-4 py-4">{flight.airline}</td>
                              <td className="px-4 py-4">{flight.day}</td>
                              <td className="px-4 py-4">{flight.delayProbability}%</td>
                              <td className="px-4 py-4">
                                <div className="flex items-center gap-3">
                                  <div className="w-24"><Progress value={flight.confidence} className="h-2" /></div>
                                  <span>{flight.confidence}%</span>
                                </div>
                              </td>
                              <td className="rounded-r-2xl px-4 py-4">
                                <Badge variant="outline" className={`rounded-full border ${statusStyles[flight.status] || statusStyles.Moderate}`}>
                                  {flight.status}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <EmptyPanel
                      title={data.recentFlights.length > 0 ? "No records match these filters" : "No saved prediction records yet"}
                      description={
                        data.recentFlights.length > 0
                          ? "Try a different airport, search term, or date range to widen the results."
                          : "Run a prediction first to populate the saved records table."
                      }
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm">
                <CardHeader>
                  <CardTitle>Raw Prediction API History</CardTitle>
                  <CardDescription>Direct database records returned by the backend predictions endpoint</CardDescription>
                </CardHeader>
                <CardContent>
                  {history.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[720px] border-separate border-spacing-y-2">
                        <thead>
                          <tr className="text-left text-sm text-blue-700">
                            <th className="px-4">Carrier</th>
                            <th className="px-4">Airport</th>
                            <th className="px-4">Month</th>
                            <th className="px-4">Result</th>
                            <th className="px-4">Probability</th>
                            <th className="px-4">Time</th>
                          </tr>
                        </thead>
                        <tbody>
                          {history.map((p) => (
                            <tr key={p.id} className="bg-sky-50 text-sm text-blue-950">
                              <td className="rounded-l-xl px-4 py-3 font-medium">{p.carrier}</td>
                              <td className="px-4 py-3">{p.airport}</td>
                              <td className="px-4 py-3">{MONTH_LABELS[p.month] || p.month}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className={`rounded-full border ${statusStyles[p.prediction_label] || statusStyles.Moderate}`}>
                                  {p.prediction_label}
                                </Badge>
                              </td>
                              <td className="px-4 py-3">{(p.delay_probability * 100).toFixed(1)}%</td>
                              <td className="rounded-r-xl px-4 py-3 text-sky-500">
                                {new Date(`${p.created_at}`).toLocaleString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <EmptyPanel
                      title="No prediction history yet"
                      description="Use the form above to save your first prediction record."
                    />
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

