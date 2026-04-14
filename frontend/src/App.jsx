import React, { useMemo, useState, useEffect } from "react";
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
  CloudRain,
  Clock3,
  Search,
  MapPin,
  TrendingUp,
  AlertTriangle,
  CalendarRange,
  Activity,
  Filter,
  RefreshCcw,
} from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = "http://localhost:5001";

const statusStyles = {
  "Low Risk": "bg-green-100 text-green-700 border-green-200",
  Moderate: "bg-yellow-100 text-yellow-700 border-yellow-200",
  "High Risk": "bg-orange-100 text-orange-700 border-orange-200",
  Critical: "bg-red-100 text-red-700 border-red-200",
};

const pieColors = ["#7dd3fc", "#818cf8", "#fde047", "#fb7185", "#34d399"];
const tooltipStyles = {
  contentStyle: { backgroundColor: "#f9fafb", borderRadius: "8px", borderColor: "#e5e7eb" },
  itemStyle: { color: "#1f2937" },
  labelStyle: { color: "#6b7280", fontSize: "12px" },
};

const EMPTY_FORM = {
  airline: "",
  origin: "",
  destination: "",
  dep_hour: "",
  day_of_week: "",
  distance: "",
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
  };

  return now - createdTime <= hours[dateRange] * 60 * 60 * 1000;
};

const validateField = (field, value) => {
  switch (field) {
    case "airline":
    case "origin":
    case "destination":
      if (!value.trim()) return "Required";
      if (!/^[A-Z0-9]{2,3}$/i.test(value.trim())) return "Must be 2-3 letters (e.g. UA, JFK)";
      return null;
    case "dep_hour": {
      const n = Number(value);
      if (value === "") return "Required";
      if (isNaN(n) || !Number.isInteger(n)) return "Must be a whole number";
      if (n < 0 || n > 23) return "Must be between 0 and 23";
      return null;
    }
    case "day_of_week": {
      const n = Number(value);
      if (value === "") return "Required";
      if (isNaN(n) || !Number.isInteger(n)) return "Must be a whole number";
      if (n < 1 || n > 7) return "Must be between 1 and 7";
      return null;
    }
    case "distance": {
      const n = Number(value);
      if (value === "") return "Required";
      if (isNaN(n) || !Number.isInteger(n)) return "Must be a whole number";
      if (n <= 0) return "Must be greater than 0";
      return null;
    }
    default:
      return null;
  }
};

function WeatherSeverityBadge({ severity }) {
  const styles = {
    low: "bg-sky-100 text-sky-700 border-sky-200",
    moderate: "bg-amber-100 text-amber-700 border-amber-200",
    high: "bg-rose-100 text-rose-700 border-rose-200",
  };

  return (
    <Badge variant="outline" className={`rounded-full border ${styles[severity] || styles.low}`}>
      {severity}
    </Badge>
  );
}

function EmptyPanel({ title, description }) {
  return (
    <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 p-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-medium text-slate-100">{title}</p>
        <p className="mt-2 text-sm text-slate-400">{description}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState({
    summaryCards: [],
    monthlyDelayData: [],
    airportRiskData: [],
    causeBreakdown: [],
    forecastData: [],
    recentFlights: [],
  });
  const [loading, setLoading] = useState(true);
  const [airportFilter, setAirportFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState("7days");

  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [comparisonBaseline, setComparisonBaseline] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/dashboard-data`);
        if (!response.ok) throw new Error("Network response was not ok");
        const json = await response.json();
        setData(json);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filteredFlights = useMemo(() => {
    return data.recentFlights.filter((flight) => {
      const matchesAirport = airportFilter === "all" || flight.airport === airportFilter;
      const matchesSearch =
        flight.id.toLowerCase().includes(search.toLowerCase()) ||
        flight.route.toLowerCase().includes(search.toLowerCase()) ||
        flight.airline.toLowerCase().includes(search.toLowerCase());
      const matchesDateRange = isWithinDateRange(flight.createdAt, dateRange);
      return matchesAirport && matchesSearch && matchesDateRange;
    });
  }, [airportFilter, search, dateRange, data.recentFlights]);

  const airportOptions = useMemo(() => {
    return [...new Set(data.recentFlights.map((flight) => flight.airport))].sort();
  }, [data.recentFlights]);

  const topAirportRisk = data.airportRiskData[0];
  const topFeature = data.causeBreakdown[0];
  const hasDashboardData =
    data.monthlyDelayData.length > 0 ||
    data.airportRiskData.length > 0 ||
    data.forecastData.length > 0 ||
    data.recentFlights.length > 0;
  const probabilityDelta = predictionResult && comparisonBaseline
    ? ((predictionResult.delay_probability - comparisonBaseline.delay_probability) * 100)
    : null;

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/predictions`);
      const json = await res.json();
      if (json.status === "success") setHistory(json.predictions);
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleFormChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: null }));
  };

  const handleBlur = (field) => {
    const error = validateField(field, form[field]);
    setFieldErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handlePredict = async () => {
    setPredicting(true);
    setPredictionResult(null);
    setPredictionError(null);

    const { airline, origin, destination, dep_hour, day_of_week, distance } = form;
    if (!airline || !origin || !destination || dep_hour === "" || day_of_week === "" || distance === "") {
      setPredictionError("Please fill in all fields before running a prediction");
      setPredicting(false);
      return;
    }

    const errors = {};
    Object.keys(form).forEach((field) => {
      const err = validateField(field, form[field]);
      if (err) errors[field] = err;
    });
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setPredictionError("Please fix the errors above before running a prediction");
      setPredicting(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          airline: form.airline,
          origin: form.origin,
          destination: form.destination,
          dep_hour: parseInt(form.dep_hour),
          day_of_week: parseInt(form.day_of_week),
          distance: parseInt(form.distance),
        }),
      });
      const json = await response.json();
      if (!response.ok || json.status === "error") {
        setPredictionError(json.message || "Prediction failed");
      } else {
        setComparisonBaseline(predictionResult);
        setPredictionResult(json);
        fetchHistory();
      }
    } catch (err) {
      setPredictionError("Could not connect to backend");
    } finally {
      setPredicting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <RefreshCcw className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-7xl p-4 md:p-8">
        <motion.div
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
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">AeroPredict</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">
              Predict flight delay risk, explore saved delay patterns, and compare scenarios in one place.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" className="rounded-2xl" onClick={() => window.location.reload()}>
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
          </div>
        </motion.div>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.summaryCards.map((card, index) => {
            const iconMap = { Plane, Clock3, CloudRain, TrendingUp };
            const Icon = iconMap[card.icon] || Plane;
            return (
              <motion.div
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
                          vs last period <span className="font-medium text-foreground">{card.change}</span>
                        </p>
                      </div>
                      <div className="rounded-2xl bg-muted p-3">
                        <Icon className="h-5 w-5" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-8">
            <CardHeader>
              <CardTitle>Monthly Delay Trends</CardTitle>
              <CardDescription>Average delay probability and predicted delay rate from saved scenarios</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {data.monthlyDelayData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.monthlyDelayData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip {...tooltipStyles} />
                    <Legend />
                    <Line type="monotone" dataKey="avgDelay" stroke="#0f172a" strokeWidth={3} name="Average delay probability" />
                    <Line type="monotone" dataKey="predicted" stroke="#2563eb" strokeWidth={3} name="Predicted delay rate" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <EmptyPanel
                  title="No monthly trend data yet"
                  description="Run and save a few predictions to start building monthly trend summaries."
                />
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
            <CardHeader>
              <CardTitle>Feature Importance</CardTitle>
              <CardDescription>How the current model weights the available flight inputs</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {data.causeBreakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={data.causeBreakdown} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={3}>
                      {data.causeBreakdown.map((entry, index) => (
                        <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip {...tooltipStyles} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <EmptyPanel
                  title="Feature metadata unavailable"
                  description="The model importance breakdown will appear here when the model metadata loads successfully."
                />
              )}
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-3 rounded-2xl bg-card p-1 shadow-sm md:w-[420px]">
            <TabsTrigger value="overview" className="rounded-xl">Overview</TabsTrigger>
            <TabsTrigger value="predictions" className="rounded-xl">Predict</TabsTrigger>
            <TabsTrigger value="flights" className="rounded-xl">Saved Flights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-7">
                <CardHeader>
                  <CardTitle>Airport Risk Snapshot</CardTitle>
                  <CardDescription>Higher scores indicate more consistently elevated delay probability</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                  {data.airportRiskData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.airportRiskData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="airport" />
                        <YAxis />
                        <Tooltip {...tooltipStyles} />
                        <Bar dataKey="risk" radius={[8, 8, 0, 0]} fill="#2563eb" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyPanel
                      title="No airport risk data yet"
                      description="Airport rankings will appear after the app has saved prediction records."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-5">
                <CardHeader>
                  <CardTitle>Summary Insights</CardTitle>
                  <CardDescription>Short interpretations of the saved prediction activity</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="rounded-2xl bg-slate-900/45 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200"><MapPin className="h-4 w-4" /> Highest current risk</div>
                    <p className="text-sm text-slate-400">
                      {topAirportRisk
                        ? `${topAirportRisk.airport} currently has the highest average delay risk in saved predictions at ${topAirportRisk.risk}%.`
                        : "Run a few predictions to populate airport-level risk insights."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-slate-900/45 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200"><CloudRain className="h-4 w-4" /> Weather signal</div>
                    <p className="text-sm text-slate-400">
                      {topFeature
                        ? `${topFeature.name} is the strongest overall feature in the current model, contributing ${topFeature.value}% of total importance.`
                        : "Feature importance will appear here once the model metadata is available."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-slate-900/45 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200"><Activity className="h-4 w-4" /> Model confidence</div>
                    <p className="text-sm text-slate-400">
                      {hasDashboardData
                        ? "Saved predictions show how the current Random Forest model scores each route for a 15+ minute departure delay."
                        : "This overview will become more informative as saved prediction history accumulates."}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="predictions">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-8">
                <CardHeader>
                  <CardTitle>Weekly Prediction Pattern</CardTitle>
                  <CardDescription>Saved scenarios grouped by the day-of-week input used in the predictor</CardDescription>
                </CardHeader>
                <CardContent className="h-[320px]">
                  {data.forecastData.some((item) => item.actual > 0 || item.predicted > 0) ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={data.forecastData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="day" />
                        <YAxis />
                        <Tooltip {...tooltipStyles} />
                        <Legend />
                        <Area type="monotone" dataKey="actual" stroke="#0f172a" fill="#cbd5e1" name="Predicted delay rate" />
                        <Area type="monotone" dataKey="predicted" stroke="#2563eb" fill="#93c5fd" name="Average delay probability" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyPanel
                      title="No weekly pattern yet"
                      description="Once predictions are saved, this chart will show how delay risk varies by selected flight day."
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
                <CardHeader>
                  <CardTitle>Run a Scenario</CardTitle>
                  <CardDescription>Enter one flight setup to generate a real-time delay prediction</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <Input placeholder="Airline (e.g. UA)" value={form.airline} onChange={(e) => handleFormChange("airline", e.target.value)} onBlur={() => handleBlur("airline")} className={`rounded-xl ${fieldErrors.airline ? "border-red-400" : ""}`} />
                    {fieldErrors.airline && <p className="mt-1 text-xs text-red-500">{fieldErrors.airline}</p>}
                  </div>
                  <div>
                    <Input placeholder="Origin (e.g. JFK)" value={form.origin} onChange={(e) => handleFormChange("origin", e.target.value)} onBlur={() => handleBlur("origin")} className={`rounded-xl ${fieldErrors.origin ? "border-red-400" : ""}`} />
                    {fieldErrors.origin && <p className="mt-1 text-xs text-red-500">{fieldErrors.origin}</p>}
                  </div>
                  <div>
                    <Input placeholder="Destination (e.g. LAX)" value={form.destination} onChange={(e) => handleFormChange("destination", e.target.value)} onBlur={() => handleBlur("destination")} className={`rounded-xl ${fieldErrors.destination ? "border-red-400" : ""}`} />
                    {fieldErrors.destination && <p className="mt-1 text-xs text-red-500">{fieldErrors.destination}</p>}
                  </div>
                  <div>
                    <Input placeholder="Departure Hour (0–23)" type="number" value={form.dep_hour} onChange={(e) => handleFormChange("dep_hour", e.target.value)} onBlur={() => handleBlur("dep_hour")} className={`rounded-xl ${fieldErrors.dep_hour ? "border-red-400" : ""}`} />
                    {fieldErrors.dep_hour && <p className="mt-1 text-xs text-red-500">{fieldErrors.dep_hour}</p>}
                  </div>
                  <div>
                    <Input placeholder="Day of Week (1=Mon, 7=Sun)" type="number" value={form.day_of_week} onChange={(e) => handleFormChange("day_of_week", e.target.value)} onBlur={() => handleBlur("day_of_week")} className={`rounded-xl ${fieldErrors.day_of_week ? "border-red-400" : ""}`} />
                    {fieldErrors.day_of_week && <p className="mt-1 text-xs text-red-500">{fieldErrors.day_of_week}</p>}
                  </div>
                  <div>
                    <Input placeholder="Distance (miles)" type="number" value={form.distance} onChange={(e) => handleFormChange("distance", e.target.value)} onBlur={() => handleBlur("distance")} className={`rounded-xl ${fieldErrors.distance ? "border-red-400" : ""}`} />
                    {fieldErrors.distance && <p className="mt-1 text-xs text-red-500">{fieldErrors.distance}</p>}
                  </div>

                  <div className="flex gap-2">
                    <Button className="flex-1 rounded-xl" onClick={handlePredict} disabled={predicting}>
                      {predicting ? "Predicting..." : "Predict Delay Risk"}
                    </Button>
                    <Button variant="outline" className="rounded-xl" onClick={() => { setForm(EMPTY_FORM); setFieldErrors({}); setPredictionResult(null); setComparisonBaseline(null); setPredictionError(null); setFlightDataContext(null); setFlightDataError(null); }}>
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
                    <div className={`rounded-xl p-4 ${predictionResult.prediction === 1 ? "bg-red-50 border border-red-200" : "bg-green-50 border border-green-200"}`}>
                      <p className={`text-lg font-semibold ${predictionResult.prediction === 1 ? "text-red-700" : "text-green-700"}`}>
                        {predictionResult.prediction_label}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        Delay probability: <span className="font-medium">{(predictionResult.delay_probability * 100).toFixed(1)}%</span>
                      </p>
                      <Progress value={predictionResult.delay_probability * 100} className="mt-2 h-2" />
                      {predictionResult.feature_importances && (
                        <div className="mt-4">
                          <p className="mb-2 text-xs font-medium text-slate-500">Top inputs influencing this result</p>
                          {predictionResult.feature_importances.map((f) => (
                            <div key={f.feature} className="mb-1">
                              <div className="flex justify-between text-xs text-slate-600 mb-0.5">
                                <span>{f.feature}</span>
                                <span>{f.importance}%</span>
                              </div>
                              <div className="h-1.5 w-full rounded-full bg-slate-200">
                                <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${f.importance}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {predictionResult?.weather_context && (
                    <div className="rounded-xl border border-slate-700 bg-slate-900/45 p-4">
                      <div className="flex items-start gap-3">
                        <div className="rounded-xl bg-slate-800 p-2 text-sky-300">
                          <CloudRain className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-slate-100">Weather Context</p>
                          <p className="mt-1 text-sm text-slate-300">{predictionResult.weather_context.headline}</p>
                          <p className="mt-2 text-sm text-slate-400">{predictionResult.weather_context.summary}</p>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        {predictionResult.weather_context.drivers.map((driver) => (
                          <div key={`${driver.label}-${driver.severity}`} className="rounded-xl bg-slate-800/80 p-3">
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-sm font-medium text-slate-100">{driver.label}</p>
                              <WeatherSeverityBadge severity={driver.severity} />
                            </div>
                            <p className="mt-2 text-sm text-slate-400">{driver.detail}</p>
                          </div>
                        ))}
                      </div>

                      <p className="mt-4 text-xs text-slate-500">{predictionResult.weather_context.disclaimer}</p>
                    </div>
                  )}

                  {predictionResult && comparisonBaseline && (
                    <div className="rounded-xl border border-slate-700 bg-slate-900/45 p-4">
                      <p className="text-sm font-medium text-slate-100">Scenario Comparison</p>
                      <p className="mt-1 text-sm text-slate-300">
                        Compared with your previous prediction, delay risk
                        <span className={`ml-1 font-medium ${probabilityDelta >= 0 ? "text-red-600" : "text-green-600"}`}>
                          {probabilityDelta >= 0 ? "increased" : "decreased"} by {Math.abs(probabilityDelta).toFixed(1)} percentage points
                        </span>.
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <div className="rounded-xl bg-slate-800/70 p-3">
                          <p className="text-slate-400">Previous</p>
                          <p className="mt-1 font-medium text-slate-100">{comparisonBaseline.input.origin} {"->"} {comparisonBaseline.input.destination}</p>
                          <p className="text-slate-300">{(comparisonBaseline.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                        <div className="rounded-xl bg-slate-800/70 p-3">
                          <p className="text-slate-400">Current</p>
                          <p className="mt-1 font-medium text-slate-100">{predictionResult.input.origin} {"->"} {predictionResult.input.destination}</p>
                          <p className="text-slate-300">{(predictionResult.delay_probability * 100).toFixed(1)}% risk</p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card className="mt-4 rounded-2xl border-none shadow-sm">
              <CardHeader>
                <CardTitle>Saved Predictions</CardTitle>
                <CardDescription>
                  {history.length > 0
                    ? `Last ${history.length} predictions saved to database`
                    : "Saved predictions will appear here after you run the form"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {history.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[800px] border-separate border-spacing-y-2">
                      <thead>
                        <tr className="text-left text-sm text-slate-400">
                          <th className="px-4">Route</th>
                          <th className="px-4">Airline</th>
                          <th className="px-4">Dep Hour</th>
                          <th className="px-4">Day</th>
                          <th className="px-4">Distance</th>
                          <th className="px-4">Result</th>
                          <th className="px-4">Probability</th>
                          <th className="px-4">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.map((p) => (
                          <tr key={p.id} className="bg-slate-900/45 text-sm text-slate-200">
                            <td className="rounded-l-xl px-4 py-3 font-medium text-slate-100">{p.origin} → {p.destination}</td>
                            <td className="px-4 py-3">{p.airline}</td>
                            <td className="px-4 py-3">{p.dep_hour}:00</td>
                            <td className="px-4 py-3">{p.day_of_week}</td>
                            <td className="px-4 py-3">{p.distance} mi</td>
                            <td className="px-4 py-3">
                              <Badge variant="outline" className={`rounded-full border ${
                                p.prediction === 1 ? "bg-red-100 text-red-700 border-red-200" : "bg-green-100 text-green-700 border-green-200"
                              }`}>
                                {p.prediction_label}
                              </Badge>
                            </td>
                            <td className="px-4 py-3">{(p.delay_probability * 100).toFixed(1)}%</td>
                            <td className="rounded-r-xl px-4 py-3 text-slate-300">{new Date(p.created_at + 'Z').toLocaleTimeString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyPanel
                    title="No prediction history yet"
                    description="Use the prediction form above to save the first record and populate this table."
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="flights">
            <Card className="rounded-2xl border-none shadow-sm">
              <CardHeader>
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <CardTitle>Flight Risk Table</CardTitle>
                    <CardDescription>Search and filter saved prediction records by route, airport, and recency</CardDescription>
                  </div>
                  <div className="grid w-full gap-3 md:grid-cols-2 xl:grid-cols-3 lg:w-auto">
                    <div className="relative min-w-[220px]">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search prediction, route, airline" className="rounded-2xl pl-10" />
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
                        <SelectItem value="24h">Last 24 Hours</SelectItem>
                        <SelectItem value="7days">Last 7 Days</SelectItem>
                        <SelectItem value="30days">Last 30 Days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex items-center gap-2 text-sm text-slate-400">
                  <Filter className="h-4 w-4" /> Showing {filteredFlights.length} saved scenarios for {dateRange}
                </div>
                {filteredFlights.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px] border-separate border-spacing-y-3">
                      <thead>
                        <tr className="text-left text-sm text-slate-400">
                          <th className="px-4">Record</th>
                          <th className="px-4">Route</th>
                          <th className="px-4">Airline</th>
                          <th className="px-4">Flight Day</th>
                          <th className="px-4">Dep Hour</th>
                          <th className="px-4">Delay Probability</th>
                          <th className="px-4">Confidence</th>
                          <th className="px-4">Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredFlights.map((flight) => (
                          <tr key={flight.id} className="rounded-2xl bg-slate-900/45 text-sm text-slate-200">
                            <td className="rounded-l-2xl px-4 py-4 font-semibold text-slate-100">{flight.id}</td>
                            <td className="px-4 py-4">{flight.route}</td>
                            <td className="px-4 py-4">{flight.airline}</td>
                            <td className="px-4 py-4">{flight.day}</td>
                            <td className="px-4 py-4">{flight.depHour}</td>
                            <td className="px-4 py-4">{flight.delayProbability}%</td>
                            <td className="px-4 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-24"><Progress value={flight.confidence} className="h-2" /></div>
                                <span>{flight.confidence}%</span>
                              </div>
                            </td>
                            <td className="rounded-r-2xl px-4 py-4">
                              <Badge variant="outline" className={`rounded-full border ${statusStyles[flight.status]}`}>
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
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
