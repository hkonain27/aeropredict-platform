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
const pieColors = ["#7dd3fc", "#818cf8", "#fde047", "#fb7185", "#34d399"];
const chartTextColor = "#cbd5e1";
const chartGridColor = "rgba(148, 163, 184, 0.28)";
const chartTooltipStyle = {
  backgroundColor: "#f9fafb",
  borderRadius: "8px",
  borderColor: "#e5e7eb",
};
const chartTooltipItemStyle = { color: "#1f2937" };
const chartTooltipLabelStyle = { color: "#6b7280", fontSize: "12px" };

const statusStyles = {
  Low: "bg-cyan-300/15 text-cyan-100 border-cyan-300/40",
  "Low Risk": "bg-cyan-300/15 text-cyan-100 border-cyan-300/40",
  "Lower Delay Risk": "bg-cyan-300/15 text-cyan-100 border-cyan-300/40",
  Medium: "bg-indigo-300/15 text-indigo-100 border-indigo-300/40",
  Moderate: "bg-indigo-300/15 text-indigo-100 border-indigo-300/40",
  "Elevated Delay Risk": "bg-indigo-300/15 text-indigo-100 border-indigo-300/40",
  High: "bg-rose-300/15 text-rose-100 border-rose-300/40",
  "High Risk": "bg-rose-300/15 text-rose-100 border-rose-300/40",
  "High Delay Risk": "bg-rose-300/15 text-rose-100 border-rose-300/40",
  Critical: "bg-rose-300/15 text-rose-100 border-rose-300/40",
};

const riskThemes = {
  low: {
    panel: "border-cyan-300/30 bg-card",
    accent: "border-cyan-300/25 bg-cyan-300/10",
    badge: "bg-cyan-300/15 text-cyan-100 border-cyan-300/30",
    title: "text-cyan-100",
    progress: "[&_[data-slot=progress-indicator]]:bg-cyan-300",
    bar: "#7dd3fc",
  },
  medium: {
    panel: "border-indigo-300/30 bg-card",
    accent: "border-indigo-300/25 bg-indigo-300/10",
    badge: "bg-indigo-300/15 text-indigo-100 border-indigo-300/30",
    title: "text-indigo-100",
    progress: "[&_[data-slot=progress-indicator]]:bg-indigo-300",
    bar: "#818cf8",
  },
  high: {
    panel: "border-rose-300/30 bg-card",
    accent: "border-rose-300/25 bg-rose-300/10",
    badge: "bg-rose-300/15 text-rose-100 border-rose-300/30",
    title: "text-rose-100",
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
    <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-border bg-muted p-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
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

  const [authToken, setAuthToken] = useState(localStorage.getItem("aero_auth_token") || "");
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ email: "", name: "", password: "" });
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [userProfile, setUserProfile] = useState(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [comparisonBaseline, setComparisonBaseline] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
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

  const authHeaders = () => {
    return authToken ? { Authorization: `Bearer ${authToken}` } : {};
  };

  const saveAuthToken = (token) => {
    localStorage.setItem("aero_auth_token", token);
    setAuthToken(token);
  };

  const clearAuth = () => {
    localStorage.removeItem("aero_auth_token");
    setAuthToken("");
    setUserProfile(null);
  };

  const loadProfile = async () => {
    if (!authToken) return;
    try {
      const response = await fetch(`${API_BASE}/api/profile`, {
        headers: authHeaders(),
      });
      if (response.status === 401) {
        clearAuth();
        return;
      }
      if (!response.ok) throw new Error("Could not load profile");
      const json = await response.json();
      if (json.status === "success") {
        setUserProfile(json.profile);
      } else {
        throw new Error(json.message || "Profile load failed");
      }
    } catch (err) {
      console.error(err);
      clearAuth();
    }
  };

  const handleAuthSubmit = async () => {
    setAuthError(null);
    setAuthLoading(true);

    if (!authForm.email || !authForm.password || (authMode === "register" && !authForm.name)) {
      setAuthError("Please fill all required fields.");
      setAuthLoading(false);
      return;
    }

    const endpoint = authMode === "login" ? "/api/login" : "/api/register";
    const payload = {
      email: authForm.email.trim(),
      password: authForm.password,
    };
    if (authMode === "register") payload.name = authForm.name.trim();

    try {
      console.log("Auth submit", { mode: authMode, endpoint: `${API_BASE}${endpoint}`, payload });
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await response.json();
      console.log("Auth response", response.status, json);
      if (!response.ok || json.status === "error") {
        setAuthError(json.message || "Authentication failed.");
      } else {
        saveAuthToken(json.token);
        setUserProfile(json.profile || null);
        setAuthForm({ email: "", name: "", password: "" });
        setAuthError(null);
      }
    } catch (err) {
      console.error(err);
      setAuthError("Could not connect to the authentication service.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/api/logout`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
      });
    } catch (err) {
      console.error(err);
    }
    clearAuth();
  };

  useEffect(() => {
    if (authToken) {
      loadProfile();
      setLoading(true);
      fetchDashboardData();
    } else {
      setLoading(false);
    }
  }, [authToken]);

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

  const getDisplayedRiskScore = (result) => result?.final_risk_score ?? result?.delay_probability;
  const probabilityDelta = predictionResult && comparisonBaseline
    ? (getDisplayedRiskScore(predictionResult) - getDisplayedRiskScore(comparisonBaseline)) * 100
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
    High: "bg-rose-300/15 text-rose-100 border-rose-300/40",
    Moderate: "bg-indigo-300/15 text-indigo-100 border-indigo-300/40",
    Low: "bg-cyan-300/15 text-cyan-100 border-cyan-300/40",
    Unknown: "bg-muted text-muted-foreground border-border",
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

  const renderAuthPage = () => (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12 text-foreground">
      <div className="w-full max-w-md space-y-6 rounded-3xl border border-border bg-card p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold text-card-foreground">AeroPredict Login</h1>
          <p className="text-sm text-muted-foreground">Create an account or sign in to save your profile and see personalized data.</p>
        </div>

        {authError && (
          <Alert className="rounded-2xl border-red-200 bg-red-50 text-red-900">
            <AlertDescription>{authError}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-card-foreground">Email</label>
            <Input
              type="email"
              value={authForm.email}
              onChange={(event) => setAuthForm((prev) => ({ ...prev, email: event.target.value }))}
              placeholder="you@example.com"
            />
          </div>
          {authMode === "register" && (
            <div>
              <label className="mb-2 block text-sm font-medium text-card-foreground">Name</label>
              <Input
                type="text"
                value={authForm.name}
                onChange={(event) => setAuthForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Your name"
              />
            </div>
          )}
          <div>
            <label className="mb-2 block text-sm font-medium text-card-foreground">Password</label>
            <Input
              type="password"
              value={authForm.password}
              onChange={(event) => setAuthForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="Enter a password"
            />
          </div>
          <Button className="w-full rounded-2xl" onClick={handleAuthSubmit} disabled={authLoading}>
            {authLoading ? "Working..." : authMode === "login" ? "Sign In" : "Create Account"}
          </Button>
        </div>

        <div className="pt-4 text-center text-sm text-muted-foreground">
          {authMode === "login" ? (
            <span>
              New here? <button className="font-semibold text-primary hover:underline" onClick={() => { setAuthMode("register"); setAuthError(null); }}>
                Create an account
              </button>
            </span>
          ) : (
            <span>
              Already have an account? <button className="font-semibold text-primary hover:underline" onClick={() => { setAuthMode("login"); setAuthError(null); }}>
                Sign in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );

  if (!authToken) {
    return renderAuthPage();
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <RefreshCcw className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-7xl p-4 md:p-8">
        <MotionDiv
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Badge className="rounded-full bg-primary px-3 py-1 text-primary-foreground hover:bg-primary">
                AeroPredict
              </Badge>
              <Badge variant="outline" className="rounded-full border-border bg-card text-muted-foreground">
                arrival delay risk
              </Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">AeroPredict</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">
              Predict flight delay risk, explore saved delay patterns, and compare scenarios in one place.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {userProfile && (
              <div className="rounded-2xl border border-border bg-card px-4 py-2 text-sm text-card-foreground">
                Signed in as <span className="font-semibold">{userProfile.name}</span>
              </div>
            )}
            <Button variant="outline" className="rounded-2xl" onClick={() => { setLoading(true); fetchDashboardData(); }}>
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
            <Button variant="ghost" className="rounded-2xl text-foreground hover:bg-muted" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </MotionDiv>

        {dashboardError && (
          <Alert className="mb-6 rounded-2xl border-border bg-card">
            <AlertTriangle className="h-4 w-4 text-primary" />
            <AlertDescription className="text-card-foreground">{dashboardError}</AlertDescription>
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
                        <p className="text-sm text-muted-foreground">{card.title}</p>
                        <h2 className="mt-2 text-3xl font-semibold">{card.value}</h2>
                        <p className="mt-2 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground">{card.change}</span>
                        </p>
                      </div>
                      <div className="rounded-2xl bg-muted p-3 text-primary">
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
                    <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                    <XAxis dataKey="monthLabel" tick={{ fill: chartTextColor }} />
                    <YAxis tick={{ fill: chartTextColor }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip
                      contentStyle={chartTooltipStyle}
                      itemStyle={chartTooltipItemStyle}
                      labelStyle={chartTooltipLabelStyle}
                      labelFormatter={(label) => `Month: ${label}`}
                      formatter={(value) => [`${value}%`, "Historical delay rate"]}
                    />
                    <Bar dataKey="avgDelay" fill="#7dd3fc" radius={[8, 8, 0, 0]} name="Historical delay rate" />
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
                    <Tooltip
                      contentStyle={chartTooltipStyle}
                      itemStyle={chartTooltipItemStyle}
                      labelStyle={chartTooltipLabelStyle}
                      formatter={(value) => `${value}%`}
                    />
                    <Legend wrapperStyle={{ color: chartTextColor }} />
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
          <TabsList className="mb-4 grid w-full grid-cols-3 rounded-2xl bg-card p-1 shadow-sm md:w-[420px]">
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
                        <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                        <XAxis dataKey="airport" tick={{ fill: chartTextColor }} />
                        <YAxis tick={{ fill: chartTextColor }} />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          itemStyle={chartTooltipItemStyle}
                          labelStyle={chartTooltipLabelStyle}
                          formatter={(value) => `${value}%`}
                        />
                        <Bar dataKey="risk" radius={[8, 8, 0, 0]} fill="#818cf8" />
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
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><MapPin className="h-4 w-4" /> Highest average risk</div>
                    <p className="text-sm text-muted-foreground">
                      {topAirportRisk
                        ? `${topAirportRisk.airport} currently has the highest average arrival delay risk in the dashboard data at ${topAirportRisk.risk}%.`
                        : "Airport-level risk insights will appear here once dashboard data is loaded."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Activity className="h-4 w-4" /> Strongest system-wide cause</div>
                    <p className="text-sm text-muted-foreground">
                      {topCause
                        ? `${prettyCauseName(topCause.name)} is currently the largest contributor to total delay minutes, accounting for about ${topCause.value}% of the overall delay burden.`
                        : "Cause-level insights will appear here when cause totals are available."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><TrendingUp className="h-4 w-4" /> What this model predicts</div>
                    <p className="text-sm text-muted-foreground">
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
                          className={`h-full min-w-0 items-start justify-start rounded-xl p-4 text-left text-sm leading-snug whitespace-normal hover:bg-card ${exampleTone.badge}`}
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
                          <span className="flex min-w-0 flex-col gap-1.5">
                            <span className="break-words text-base font-semibold leading-tight">
                              {example.risk || "Example"} risk
                            </span>
                            <span className="break-words text-base leading-tight">
                              {example.carrier} @ {example.airport} in {monthName(example.month)}
                            </span>
                            <span className="break-words text-sm leading-snug text-primary">
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
                      className={`rounded-xl ${fieldErrors.carrier ? "border-primary ring-1 ring-primary/40" : ""}`}
                    />
                    {fieldErrors.carrier && <p className="mt-1 text-xs text-foreground">{fieldErrors.carrier}</p>}
                  </div>

                  <div>
                    <Input
                      placeholder="Airport code (e.g. CLT)"
                      value={form.airport}
                      onChange={(e) => handleFormChange("airport", e.target.value)}
                      onBlur={() => handleBlur("airport")}
                      className={`rounded-xl ${fieldErrors.airport ? "border-primary ring-1 ring-primary/40" : ""}`}
                    />
                    {fieldErrors.airport && <p className="mt-1 text-xs text-foreground">{fieldErrors.airport}</p>}
                  </div>

                  <div>
                    <Select value={form.month} onValueChange={(value) => handleFormChange("month", value)}>
                      <SelectTrigger className={`rounded-xl ${fieldErrors.month ? "border-primary ring-1 ring-primary/40" : ""}`}>
                        <SelectValue placeholder="Select month" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(MONTH_LABELS).map(([value, label]) => (
                          <SelectItem key={value} value={String(value)}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {fieldErrors.month && <p className="mt-1 text-xs text-foreground">{fieldErrors.month}</p>}
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
                    <Alert className="rounded-xl border-border bg-card">
                      <AlertTriangle className="h-4 w-4 text-foreground" />
                      <AlertDescription className="text-foreground">{predictionError}</AlertDescription>
                    </Alert>
                  )}

                  {predictionResult && (
                    <div className={`rounded-xl border p-5 ${riskTheme.panel}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={`text-xl font-semibold ${riskTheme.title}`}>
                            {displayRiskLabel}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {predictionResult.input.carrier} at {predictionResult.input.airport} in {monthName(predictionResult.input.month)}.
                          </p>
                        </div>
                        <Badge variant="outline" className={`rounded-full border px-3 py-1 text-sm ${riskTheme.badge}`}>
                          {finalRiskScore !== undefined ? `${(finalRiskScore * 100).toFixed(1)}%` : `${(predictionResult.delay_probability * 100).toFixed(1)}%`}
                        </Badge>
                      </div>

                      <Progress value={(finalRiskScore ?? predictionResult.delay_probability) * 100} className={`mt-4 h-3 bg-card ${riskTheme.progress}`} />

                      {keyTakeaway && (
                        <div className={`mt-4 rounded-xl border border-border p-4 ${riskTheme.accent}`}>
                          <p className="text-sm font-semibold text-foreground">Key Takeaway</p>
                          <p className="mt-1 text-sm text-muted-foreground">{keyTakeaway}</p>
                        </div>
                      )}

                      <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                        <div className="rounded-xl border border-border bg-background/40 p-3">
                          <p className="text-primary">Raw model</p>
                          <p className="mt-1 font-semibold text-foreground">
                            {rawModel ? `${(rawModel.delay_probability * 100).toFixed(1)}%` : "n/a"}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">{rawModel?.prediction_label || "Model result unavailable"}</p>
                        </div>
                        <div className="rounded-xl border border-border bg-background/40 p-3">
                          <p className="text-primary">2024 evidence</p>
                          <p className="mt-1 font-semibold text-foreground">
                            {flight2024Summary ? contextualPercent(flight2024Summary.delay_rate) : "n/a"}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">{recentDelayComparison || flight2024Risk?.level || "Recent context unavailable"}</p>
                        </div>
                        <div className="rounded-xl border border-border bg-background/40 p-3">
                          <p className="text-primary">Historical weather</p>
                          <p className="mt-1 font-semibold text-foreground">
                            {historicalWeather?.available ? (historicalWeatherRisk?.level || "Reported") : "Unavailable"}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {historicalWeather?.available
                              ? `${formatPercentValue(historicalWeather.precipitation_rate)} precipitation observations`
                              : "No weather context available"}
                          </p>
                        </div>
                      </div>
                      {riskContributionData.length > 0 && (
                        <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4">
                          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-foreground">What's driving this prediction</p>
                              <p className="mt-1 text-sm text-muted-foreground">Shows how each factor contributed to final risk.</p>
                            </div>
                            <Badge variant="outline" className="w-fit rounded-full border-border bg-muted text-muted-foreground">
                              month analysis
                            </Badge>
                          </div>
                          <div className="h-[210px]">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={riskContributionData} layout="vertical" margin={{ left: 20, right: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGridColor} />
                                <XAxis type="number" domain={[0, 50]} tick={{ fill: chartTextColor }} tickFormatter={(value) => `${value}%`} />
                                <YAxis type="category" dataKey="name" width={116} tick={{ fill: chartTextColor, fontSize: 12 }} />
                                <Tooltip
                                  contentStyle={chartTooltipStyle}
                                  itemStyle={chartTooltipItemStyle}
                                  labelStyle={chartTooltipLabelStyle}
                                  formatter={(value, name, props) => {
                                    if (name === "contribution") return [`${value}%`, "Final-score contribution"];
                                    return [`${props.payload.weight}%`, "Effective weight"];
                                  }}
                                />
                                <Bar dataKey="contribution" fill={riskTheme.bar} radius={[0, 8, 8, 0]}>
                                  <LabelList dataKey="contribution" position="right" fill={chartTextColor} formatter={(value) => `${value}%`} />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}

                      {flight2024Context && (
                        <div className="mt-4 space-y-3 rounded-xl border border-border bg-muted/40 p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-foreground">Recent (2024) flight behavior</p>
                              <p className="mt-1 text-sm text-muted-foreground">Recent flights show whether this route has been behaving better or worse than its longer-term pattern.</p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${weatherRiskStyles[flight2024Risk?.level] || weatherRiskStyles.Unknown}`}>
                              {flight2024Risk?.level || "Unknown"}
                            </Badge>
                          </div>

                          {flight2024Context.available && flight2024Summary ? (
                            <>
                              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Flights</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {formatCount(flight2024Summary.flights)}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Delay rate</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {contextualPercent(flight2024Summary.delay_rate)}
                                  </p>
                                  {recentDelayComparison && <p className="mt-1 text-sm text-muted-foreground">{recentDelayComparison}</p>}
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Cancelled</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {contextualPercent(flight2024Summary.cancellation_rate, "flights")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Avg delay</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {formatDelayMinutes(flight2024Summary.avg_arrival_delay_minutes)}
                                  </p>
                                </div>
                              </div>

                              {flight2024Risk?.drivers?.length > 0 && (
                                <ul className="space-y-1 text-sm text-muted-foreground">
                                  {flight2024Risk.drivers.slice(0, 2).map((driver) => (
                                    <li key={driver}>{driver}</li>
                                  ))}
                                </ul>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              {flight2024Context.message || "No 2024 flight evidence is available for this airport-airline-month combination."}
                            </p>
                          )}
                        </div>
                      )}

                      {(historicalWeather || historicalWeatherRisk) && (
                        <div className="mt-4 space-y-3 rounded-xl border border-border bg-muted/40 p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-foreground">Historical weather pattern</p>
                              <p className="mt-1 text-sm text-muted-foreground">
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
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Observations</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {formatCount(historicalWeather.observations)}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Low visibility</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {contextualPercent(historicalWeather.low_visibility_rate, "observations")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Gusty wind</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {contextualPercent(historicalWeather.gusty_wind_rate, "observations")}
                                  </p>
                                </div>
                                <div className="rounded-xl bg-background/40 p-3">
                                  <p className="text-primary">Precipitation</p>
                                  <p className="mt-1 text-lg font-semibold text-foreground">
                                    {contextualPercent(historicalWeather.precipitation_rate, "observations")}
                                  </p>
                                </div>
                              </div>

                              {historicalWeatherRisk?.drivers?.length > 0 && (
                                <ul className="space-y-1 text-sm text-muted-foreground">
                                  {historicalWeatherRisk.drivers.slice(0, 2).map((driver) => (
                                    <li key={driver}>{driver}</li>
                                  ))}
                                </ul>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              {historicalWeatherRisk?.drivers?.[0] || "Historical airport weather is unavailable."}
                            </p>
                          )}
                        </div>
                      )}

                      {currentAnalysis && (
                        <div className="mt-4 space-y-4 rounded-xl border border-border bg-muted/40 p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-foreground">Long-term delay trends</p>
                              <p className="mt-1 text-sm text-muted-foreground">This compares the selected airline and airport against the typical month pattern.</p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${statusStyles[currentAnalysis.risk_label] || statusStyles.Moderate}`}>
                              {currentAnalysis.risk_label}
                            </Badge>
                          </div>

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div className="rounded-xl bg-background/40 p-3">
                              <p className="text-primary">Historical delay rate</p>
                              <p className="mt-1 text-xl font-semibold text-foreground">
                                {contextualPercent(historicalContext?.delay_rate)}
                              </p>
                              {historicalDelayComparison && <p className="mt-1 text-sm text-muted-foreground">{historicalDelayComparison}</p>}
                            </div>
                            <div className="rounded-xl bg-background/40 p-3">
                              <p className="text-primary">Month baseline</p>
                              <p className="mt-1 text-xl font-semibold text-foreground">
                                {contextualPercent(monthBaseline?.delay_rate)}
                              </p>
                            </div>
                            <div className="rounded-xl bg-background/40 p-3">
                              <p className="text-primary">Exact matches</p>
                              <p className="mt-1 text-xl font-semibold text-foreground">
                                {currentAnalysis.availability.exact_matches}
                              </p>
                            </div>
                            <div className="rounded-xl bg-background/40 p-3">
                              <p className="text-primary">Average delay minutes</p>
                              <p className="mt-1 text-xl font-semibold text-foreground">
                                {formatDelayMinutes(historicalContext?.avg_delay_minutes_per_delayed_arrival)}
                              </p>
                            </div>
                          </div>

                          {causeMix.length > 0 && (
                            <div className="space-y-3">
                              <p className="text-sm font-medium text-foreground">
                                Primary cause: {prettyCauseName(primaryCause.name)} ({primaryCause.share}%)
                              </p>
                              {secondaryCause && (
                                <p className="text-sm text-muted-foreground">
                                  Secondary: {prettyCauseName(secondaryCause.name)} ({secondaryCause.share}%)
                                </p>
                              )}
                              {causeMix
                                .filter((item) => item.share > 0)
                                .sort((a, b) => b.share - a.share)
                                .slice(0, 4)
                                .map((item) => (
                                  <div key={item.name}>
                                    <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                                      <span>{item.name}</span>
                                      <span>{item.share}%</span>
                                    </div>
                                    <div className="h-1.5 w-full rounded-full bg-border">
                                      <div className="h-1.5 rounded-full bg-primary" style={{ width: `${item.share}%` }} />
                                    </div>
                                  </div>
                                ))}
                            </div>
                          )}
                        </div>
                      )}

                      {(liveWeather || weatherRisk) && (
                        <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p className="text-base font-semibold text-foreground">Live current conditions</p>
                              <p className="mt-1 text-sm text-muted-foreground">
                                This is current weather, not for the selected month, and is not used in the {monthName(predictionResult.input.month)} score.
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-2 text-sm">
                              <Badge variant="outline" className={`rounded-full border ${weatherRiskBadgeClass}`}>
                                {liveWeather?.available ? (liveWeather.flight_category || "Reported") : "Unavailable"}
                              </Badge>
                              {liveWeather?.available && (
                                <>
                                  <Badge variant="outline" className="rounded-full border-border bg-card text-muted-foreground">
                                    {liveWeather.visibility_miles ?? "n/a"} mi
                                  </Badge>
                                  <Badge variant="outline" className="rounded-full border-border bg-card text-muted-foreground">
                                    {liveWeather.wind_speed_kt ?? "n/a"} kt wind
                                  </Badge>
                                </>
                              )}
                            </div>
                          </div>
                          {!liveWeather?.available && (
                            <p className="mt-3 text-sm text-muted-foreground">
                              {liveWeather?.message || "Live weather is not currently available for this airport."}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {predictionResult && comparisonBaseline && (
                    <div className="rounded-xl border border-border bg-muted/40 p-4">
                      <p className="text-sm font-medium text-foreground">Scenario Comparison</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Compared with your previous prediction, delay risk
                        <span className={`ml-1 font-medium ${probabilityDelta >= 0 ? "text-foreground" : "text-cyan-300"}`}>
                          {probabilityDelta >= 0 ? " increased " : " decreased "}
                          by {Math.abs(probabilityDelta).toFixed(1)} percentage points
                        </span>
                        .
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div className="rounded-xl bg-background/40 p-3">
                          <p className="text-primary">Previous</p>
                          <p className="mt-1 font-medium">{comparisonBaseline.input.carrier} @ {comparisonBaseline.input.airport}</p>
                          <p className="text-muted-foreground">{(getDisplayedRiskScore(comparisonBaseline) * 100).toFixed(1)}% risk</p>
                        </div>
                        <div className="rounded-xl bg-background/40 p-3">
                          <p className="text-primary">Current</p>
                          <p className="mt-1 font-medium">{predictionResult.input.carrier} @ {predictionResult.input.airport}</p>
                          <p className="text-muted-foreground">{(getDisplayedRiskScore(predictionResult) * 100).toFixed(1)}% risk</p>
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
                        <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                        <XAxis type="number" tick={{ fill: chartTextColor }} tickFormatter={(value) => `${value}%`} />
                        <YAxis
                          type="category"
                          dataKey="carrierName"
                          width={150}
                          interval={0}
                          tick={{ fill: chartTextColor, fontSize: 12 }}
                        />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          itemStyle={chartTooltipItemStyle}
                          labelStyle={chartTooltipLabelStyle}
                          formatter={(value) => [`${value}%`, "Airline delay rate"]}
                          labelFormatter={(label, items) => {
                            const carrier = items?.[0]?.payload?.carrier;
                            return carrier ? `${label} (${carrier})` : label;
                          }}
                        />
                        <Bar dataKey="actual" fill="#34d399" radius={[8, 8, 0, 0]} name="Carrier delay rate" />
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
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary" />
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
                  <div className="mb-4 flex items-center gap-2 text-sm text-primary">
                    <Filter className="h-4 w-4" /> Showing {filteredFlights.length} saved records
                  </div>
                  {filteredFlights.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[820px] border-separate border-spacing-y-3">
                        <thead>
                          <tr className="text-left text-sm text-primary">
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
                            <tr key={flight.id} className="bg-muted text-sm text-foreground">
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

            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
