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
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
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
const pieColors = ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"];

const statusStyles = {
  "Low Risk": "bg-green-100 text-green-700 border-green-200",
  "Lower Delay Risk": "bg-green-100 text-green-700 border-green-200",
  Moderate: "bg-yellow-100 text-yellow-700 border-yellow-200",
  "Elevated Delay Risk": "bg-yellow-100 text-yellow-700 border-yellow-200",
  "High Risk": "bg-orange-100 text-orange-700 border-orange-200",
  "High Delay Risk": "bg-red-100 text-red-700 border-red-200",
  Critical: "bg-red-100 text-red-700 border-red-200",
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
};

const normalizeDashboardData = (payload = {}) => ({
  summaryCards: Array.isArray(payload.summaryCards) ? payload.summaryCards : [],
  monthlyDelayData: Array.isArray(payload.monthlyDelayData) ? payload.monthlyDelayData : [],
  airportRiskData: Array.isArray(payload.airportRiskData) ? payload.airportRiskData : [],
  causeBreakdown: Array.isArray(payload.causeBreakdown) ? payload.causeBreakdown : [],
  forecastData: Array.isArray(payload.forecastData) ? payload.forecastData : [],
  recentFlights: Array.isArray(payload.recentFlights) ? payload.recentFlights : [],
});

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  return `${(Number(value) * 100).toFixed(1)}%`;
};

const formatCount = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  return Number(value).toLocaleString();
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
    <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-medium text-slate-700">{title}</p>
        <p className="mt-2 text-sm text-slate-500">{description}</p>
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
    const carriers = data.forecastData.map((item) => item.day).filter(Boolean);
    const airports = data.airportRiskData.map((item) => item.airport).filter(Boolean);
    const fallbackCarriers = ["AA", "DL", "UA"];
    const fallbackAirports = ["CLT", "ATL", "ORD"];
    const months = highestDelayMonths.length > 0 ? highestDelayMonths : ["12", "7", "1"];

    return [0, 1, 2].map((index) => ({
      carrier: carriers[index] || fallbackCarriers[index],
      airport: airports[index] || fallbackAirports[index],
      month: months[index] || months[0],
    }));
  }, [data.airportRiskData, data.forecastData, highestDelayMonths]);

  const probabilityDelta = predictionResult && comparisonBaseline
    ? (predictionResult.delay_probability - comparisonBaseline.delay_probability) * 100
    : null;
  const currentAnalysis = predictionResult?.analysis;
  const historicalContext = currentAnalysis?.historical?.context_used;
  const exactHistorical = currentAnalysis?.historical?.exact;
  const monthBaseline = currentAnalysis?.historical?.month_baseline;
  const causeMix = historicalContext?.cause_breakdown || [];
  const matchedRecords = currentAnalysis?.matched_records || [];
  const displayRiskLabel = currentAnalysis?.risk_label || predictionResult?.prediction_label;
  const predictionPanelClass = displayRiskLabel === "High Delay Risk"
    ? "border-red-200 bg-red-50"
    : displayRiskLabel === "Elevated Delay Risk"
      ? "border-yellow-200 bg-yellow-50"
      : "border-green-200 bg-green-50";
  const predictionTitleClass = displayRiskLabel === "High Delay Risk"
    ? "text-red-700"
    : displayRiskLabel === "Elevated Delay Risk"
      ? "text-yellow-700"
      : "text-green-700";

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <RefreshCcw className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
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
                Aviation Intelligence Platform
              </Badge>
              <Badge variant="outline" className="rounded-full border-slate-200 bg-white text-slate-600">
                arrival delay risk
              </Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Airport-Airline Delay Risk Dashboard</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600 md:text-base">
              Explore BTS arrival-delay trends by airline and airport, compare operational causes, and score delay risk using carrier, airport, and month.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" className="rounded-2xl" onClick={() => { setLoading(true); fetchDashboardData(); fetchHistory(); }}>
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
          </div>
        </MotionDiv>

        {dashboardError && (
          <Alert className="mb-6 rounded-2xl border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <AlertDescription className="text-red-700">{dashboardError}</AlertDescription>
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
                        <p className="text-sm text-slate-500">{card.title}</p>
                        <h2 className="mt-2 text-3xl font-semibold">{card.value}</h2>
                        <p className="mt-2 text-sm text-slate-500">
                          <span className="font-medium text-slate-700">{card.change}</span>
                        </p>
                      </div>
                      <div className="rounded-2xl bg-slate-100 p-3">
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
                  <LineChart data={data.monthlyDelayData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Legend />
                    <Line type="monotone" dataKey="avgDelay" stroke="#0f172a" strokeWidth={3} name="Observed delay rate" />
                    <Line type="monotone" dataKey="predicted" stroke="#2563eb" strokeWidth={3} name="Dashboard risk reference" />
                  </LineChart>
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

        <Tabs defaultValue="overview" className="w-full">
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
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><MapPin className="h-4 w-4" /> Highest average risk</div>
                    <p className="text-sm text-slate-600">
                      {topAirportRisk
                        ? `${topAirportRisk.airport} currently has the highest average arrival delay risk in the dashboard data at ${topAirportRisk.risk}%.`
                        : "Airport-level risk insights will appear here once dashboard data is loaded."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Activity className="h-4 w-4" /> Strongest system-wide cause</div>
                    <p className="text-sm text-slate-600">
                      {topCause
                      ? `${prettyCauseName(topCause.name)} is currently the largest contributor to total delay minutes, accounting for about ${topCause.value}% of the overall delay burden.`
                      : "Cause-level insights will appear here when cause totals are available."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><TrendingUp className="h-4 w-4" /> What this model predicts</div>
                    <p className="text-sm text-slate-600">
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
                  <CardTitle>Carrier Risk Comparison</CardTitle>
                  <CardDescription>Top carrier-level delay rates from the real dashboard dataset</CardDescription>
                </CardHeader>
                <CardContent className="h-[320px]">
                  {data.forecastData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={data.forecastData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" />
                        <YAxis />
                        <Tooltip formatter={(value) => `${value}%`} />
                        <Legend />
                        <Area type="monotone" dataKey="actual" stroke="#0f172a" fill="#cbd5e1" name="Observed delay rate" />
                        <Area type="monotone" dataKey="predicted" stroke="#2563eb" fill="#93c5fd" name="Dashboard risk reference" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyPanel
                      title="No carrier comparison yet"
                      description="Carrier-level trend data will appear here when the backend dashboard route is wired up."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-5">
                <CardHeader>
                  <CardTitle>Search Delay Risk</CardTitle>
                  <CardDescription>Enter a carrier, airport, and month to compare model risk with BTS history</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    {formExamples.map((example) => (
                      <Button
                        key={`${example.carrier}-${example.airport}-${example.month}`}
                        variant="outline"
                        className="rounded-xl text-xs"
                        onClick={() => {
                          setForm(example);
                          setFieldErrors({});
                          setPredictionError(null);
                        }}
                      >
                        {example.carrier} @ {example.airport}
                      </Button>
                    ))}
                  </div>

                  <div>
                    <Input
                      placeholder="Carrier code (e.g. AA)"
                      value={form.carrier}
                      onChange={(e) => handleFormChange("carrier", e.target.value)}
                      onBlur={() => handleBlur("carrier")}
                      className={`rounded-xl ${fieldErrors.carrier ? "border-red-400" : ""}`}
                    />
                    {fieldErrors.carrier && <p className="mt-1 text-xs text-red-500">{fieldErrors.carrier}</p>}
                  </div>

                  <div>
                    <Input
                      placeholder="Airport code (e.g. CLT)"
                      value={form.airport}
                      onChange={(e) => handleFormChange("airport", e.target.value)}
                      onBlur={() => handleBlur("airport")}
                      className={`rounded-xl ${fieldErrors.airport ? "border-red-400" : ""}`}
                    />
                    {fieldErrors.airport && <p className="mt-1 text-xs text-red-500">{fieldErrors.airport}</p>}
                  </div>

                  <div>
                    <Select value={form.month} onValueChange={(value) => handleFormChange("month", value)}>
                      <SelectTrigger className={`rounded-xl ${fieldErrors.month ? "border-red-400" : ""}`}>
                        <SelectValue placeholder="Select month" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(MONTH_LABELS).map(([value, label]) => (
                          <SelectItem key={value} value={String(value)}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {fieldErrors.month && <p className="mt-1 text-xs text-red-500">{fieldErrors.month}</p>}
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
                    <Alert className="rounded-xl border-red-200 bg-red-50">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      <AlertDescription className="text-red-700">{predictionError}</AlertDescription>
                    </Alert>
                  )}

                  {predictionResult && (
                    <div className={`rounded-xl border p-4 ${predictionPanelClass}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={`text-lg font-semibold ${predictionTitleClass}`}>
                            {displayRiskLabel}
                          </p>
                          <p className="mt-1 text-sm text-slate-600">
                            {predictionResult.input.carrier} at {predictionResult.input.airport} in {MONTH_LABELS[predictionResult.input.month]}.
                          </p>
                        </div>
                        <Badge variant="outline" className={`rounded-full border ${statusStyles[currentAnalysis?.risk_label || predictionResult.prediction_label] || statusStyles["Moderate"]}`}>
                          {(predictionResult.delay_probability * 100).toFixed(1)}%
                        </Badge>
                      </div>

                      <Progress value={predictionResult.delay_probability * 100} className="mt-3 h-2" />
                      <p className="mt-2 text-xs text-slate-500">
                        Model score means this scenario looks delay-heavy compared with the training data.
                      </p>

                      {currentAnalysis && (
                        <div className="mt-4 space-y-4 rounded-xl border border-slate-200 bg-white p-4">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-sm font-medium text-slate-800">Historical BTS match</p>
                              <p className="mt-1 text-sm text-slate-600">
                                {historicalContext?.label || "No matching historical context found"} - {currentAnalysis.historical.reliability} evidence
                              </p>
                            </div>
                            <Badge variant="outline" className={`w-fit rounded-full border ${statusStyles[currentAnalysis.risk_label] || statusStyles["Moderate"]}`}>
                              {currentAnalysis.risk_label}
                            </Badge>
                          </div>

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div className="rounded-xl bg-slate-50 p-3">
                              <p className="text-slate-500">Historical delay rate</p>
                              <p className="mt-1 text-xl font-semibold text-slate-900">
                                {formatPercent(historicalContext?.delay_rate)}
                              </p>
                              <p className="text-xs text-slate-500">
                                {formatCount(historicalContext?.delayed_arrivals)} delayed of {formatCount(historicalContext?.arrivals)}
                              </p>
                            </div>
                            <div className="rounded-xl bg-slate-50 p-3">
                              <p className="text-slate-500">Month baseline</p>
                              <p className="mt-1 text-xl font-semibold text-slate-900">
                                {formatPercent(monthBaseline?.delay_rate)}
                              </p>
                              <p className="text-xs text-slate-500">
                                {monthBaseline ? `${monthBaseline.records} BTS rows in ${MONTH_LABELS[predictionResult.input.month]}` : "No baseline"}
                              </p>
                            </div>
                            <div className="rounded-xl bg-slate-50 p-3">
                              <p className="text-slate-500">Exact matches</p>
                              <p className="mt-1 text-xl font-semibold text-slate-900">
                                {currentAnalysis.availability.exact_matches}
                              </p>
                              <p className="text-xs text-slate-500">
                                {exactHistorical?.years?.length ? `${exactHistorical.years[0]}-${exactHistorical.years[exactHistorical.years.length - 1]}` : "Using nearest context"}
                              </p>
                            </div>
                            <div className="rounded-xl bg-slate-50 p-3">
                              <p className="text-slate-500">Average delay minutes</p>
                              <p className="mt-1 text-xl font-semibold text-slate-900">
                                {historicalContext?.avg_delay_minutes_per_delayed_arrival ?? "n/a"}
                              </p>
                              <p className="text-xs text-slate-500">per delayed arrival</p>
                            </div>
                          </div>

                          {causeMix.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Main historical delay causes</p>
                              {causeMix
                                .filter((item) => item.share > 0)
                                .sort((a, b) => b.share - a.share)
                                .slice(0, 4)
                                .map((item) => (
                                  <div key={item.name}>
                                    <div className="mb-1 flex justify-between text-xs text-slate-600">
                                      <span>{item.name}</span>
                                      <span>{item.share}%</span>
                                    </div>
                                    <div className="h-1.5 w-full rounded-full bg-slate-200">
                                      <div className="h-1.5 rounded-full bg-slate-900" style={{ width: `${item.share}%` }} />
                                    </div>
                                  </div>
                                ))}
                            </div>
                          )}

                          {matchedRecords.length > 0 && (
                            <div className="overflow-x-auto">
                              <table className="w-full min-w-[520px] border-separate border-spacing-y-2 text-xs">
                                <thead>
                                  <tr className="text-left text-slate-500">
                                    <th className="px-3">Year</th>
                                    <th className="px-3">Carrier</th>
                                    <th className="px-3">Airport</th>
                                    <th className="px-3">Arrivals</th>
                                    <th className="px-3">Delay rate</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {matchedRecords.slice(0, 5).map((record) => (
                                    <tr key={`${record.year}-${record.carrier}-${record.airport}-${record.month}`} className="bg-slate-50 text-slate-800">
                                      <td className="rounded-l-xl px-3 py-2">{record.year}</td>
                                      <td className="px-3 py-2">{record.carrier}</td>
                                      <td className="px-3 py-2">{record.airport}</td>
                                      <td className="px-3 py-2">{formatCount(record.arrivals)}</td>
                                      <td className="rounded-r-xl px-3 py-2">{formatPercent(record.delay_rate)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )}

                      {predictionResult.feature_importances?.length > 0 && (
                        <div className="mt-4 space-y-2">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">What influenced this score</p>
                          {predictionResult.feature_importances.map((item) => (
                            <div key={item.feature}>
                              <div className="mb-1 flex justify-between text-xs text-slate-600">
                                <span>{item.feature.replaceAll("_", " ")}</span>
                                <span>{item.importance}%</span>
                              </div>
                              <div className="h-1.5 w-full rounded-full bg-slate-200">
                                <div className="h-1.5 rounded-full bg-blue-600" style={{ width: `${item.importance}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {predictionResult && comparisonBaseline && (
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                      <p className="text-sm font-medium text-slate-800">Scenario Comparison</p>
                      <p className="mt-1 text-sm text-slate-600">
                        Compared with your previous prediction, delay risk
                        <span className={`ml-1 font-medium ${probabilityDelta >= 0 ? "text-red-600" : "text-green-600"}`}>
                          {probabilityDelta >= 0 ? " increased " : " decreased "}
                          by {Math.abs(probabilityDelta).toFixed(1)} percentage points
                        </span>
                        .
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-slate-500">Previous</p>
                          <p className="mt-1 font-medium">{comparisonBaseline.input.carrier} @ {comparisonBaseline.input.airport}</p>
                          <p className="text-slate-600">{(comparisonBaseline.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-slate-500">Current</p>
                          <p className="mt-1 font-medium">{predictionResult.input.carrier} @ {predictionResult.input.airport}</p>
                          <p className="text-slate-600">{(predictionResult.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                      </div>
                    </div>
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
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
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
                  <div className="mb-4 flex items-center gap-2 text-sm text-slate-500">
                    <Filter className="h-4 w-4" /> Showing {filteredFlights.length} saved records
                  </div>
                  {filteredFlights.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[820px] border-separate border-spacing-y-3">
                        <thead>
                          <tr className="text-left text-sm text-slate-500">
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
                            <tr key={flight.id} className="bg-slate-50 text-sm text-slate-800">
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
                                <Badge variant="outline" className={`rounded-full border ${statusStyles[flight.status] || statusStyles["Moderate"]}`}>
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
                          <tr className="text-left text-sm text-slate-500">
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
                            <tr key={p.id} className="bg-slate-50 text-sm text-slate-800">
                              <td className="rounded-l-xl px-4 py-3 font-medium">{p.carrier}</td>
                              <td className="px-4 py-3">{p.airport}</td>
                              <td className="px-4 py-3">{MONTH_LABELS[p.month] || p.month}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className={`rounded-full border ${statusStyles[p.prediction_label] || statusStyles["Moderate"]}`}>
                                  {p.prediction_label}
                                </Badge>
                              </td>
                              <td className="px-4 py-3">{(p.delay_probability * 100).toFixed(1)}%</td>
                              <td className="rounded-r-xl px-4 py-3 text-slate-400">
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
