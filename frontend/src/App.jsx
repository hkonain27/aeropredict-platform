import React, { useMemo, useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

const statusStyles = {
  "Low Risk": "bg-green-100 text-green-700 border-green-200",
  Moderate: "bg-yellow-100 text-yellow-700 border-yellow-200",
  "High Risk": "bg-orange-100 text-orange-700 border-orange-200",
  Critical: "bg-red-100 text-red-700 border-red-200",
};

const pieColors = ["#7dd3fc", "#818cf8", "#fde047", "#fb7185", "#34d399"];

const EMPTY_FORM = {
  airline: "",
  origin: "",
  destination: "",
  dep_hour: "",
  day_of_week: "",
  distance: "",
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

export default function App() {
  const [data, setData] = useState({
    summaryCards: [],
    monthlyDelayData: [],
    airportRiskData: [],
    causeBreakdown: [],
    forecastData: [],
    mockFlights: [],
  });
  const [loading, setLoading] = useState(true);
  const [airportFilter, setAirportFilter] = useState("all");
  const [weatherFilter, setWeatherFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState("7days");

  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://localhost:5001/api/dashboard-data");
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
    return data.mockFlights.filter((flight) => {
      const matchesAirport = airportFilter === "all" || flight.airport === airportFilter;
      const matchesWeather = weatherFilter === "all" || flight.weather.toLowerCase() === weatherFilter.toLowerCase();
      const matchesSearch =
        flight.id.toLowerCase().includes(search.toLowerCase()) ||
        flight.route.toLowerCase().includes(search.toLowerCase()) ||
        flight.airline.toLowerCase().includes(search.toLowerCase());
      return matchesAirport && matchesWeather && matchesSearch;
    });
  }, [airportFilter, weatherFilter, search, data.mockFlights]);

  const fetchHistory = async () => {
    try {
      const res = await fetch("http://localhost:5001/predictions");
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
      const response = await fetch("http://localhost:5001/predict", {
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
                Aviation Intelligence Platform
              </Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Flight Delay Prediction Dashboard</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">
              Monitor historic delay patterns, compare weather impact, and run real-time delay predictions.
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
                      <div className="rounded-2xl bg-muted-foreground p-3">
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
              <CardTitle>Delay Trends vs Model Prediction</CardTitle>
              <CardDescription>Historic monthly average delay compared to model output</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.monthlyDelayData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#f9fafb", borderRadius: "8px", borderColor: "#e5e7eb" }}
                    itemStyle={{ color: "#1f2937" }}
                    labelStyle={{ color: "#6b7280", fontSize: "12px" }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="avgDelay" stroke="#0f172a" strokeWidth={3} name="Actual Avg Delay" />
                  <Line type="monotone" dataKey="predicted" stroke="#2563eb" strokeWidth={3} name="Predicted Delay" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
            <CardHeader>
              <CardTitle>Delay Cause Breakdown</CardTitle>
              <CardDescription>What appears to drive delays most often</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.causeBreakdown} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={3}>
                    {data.causeBreakdown.map((entry, index) => (
                      <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#f9fafb", borderRadius: "8px", borderColor: "#e5e7eb" }}
                    itemStyle={{ color: "#1f2937" }}
                    labelStyle={{ color: "#6b7280", fontSize: "12px" }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-3 rounded-2xl bg-card p-1 shadow-sm md:w-[420px]">
            <TabsTrigger value="overview" className="rounded-xl">Overview</TabsTrigger>
            <TabsTrigger value="predictions" className="rounded-xl">Predictions</TabsTrigger>
            <TabsTrigger value="flights" className="rounded-xl">Flights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-7">
                <CardHeader>
                  <CardTitle>Airport Delay Risk Index</CardTitle>
                  <CardDescription>Higher score means more consistent delay risk across recent data</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.airportRiskData} >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="airport" />
                      <YAxis />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#f9fafb", borderRadius: "8px", borderColor: "#e5e7eb" }}
                        itemStyle={{ color: "#1f2937" }}
                        labelStyle={{ color: "#6b7280", fontSize: "12px" }}
                      />
                      <Bar dataKey="risk" radius={[8, 8, 0, 0]} fill="#2563eb"/>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-5">
                <CardHeader>
                  <CardTitle>Operational Insights</CardTitle>
                  <CardDescription>Quick-glance interpretation for decision-makers</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-600"><MapPin className="h-4 w-4" /> Highest current risk</div>
                    <p className="text-sm text-slate-600">ORD and ATL show the strongest sustained delay risk based on January 2024 flight data.</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-600"><CloudRain className="h-4 w-4" /> Weather signal</div>
                    <p className="text-sm text-slate-600">Departure hour and distance are the strongest numeric predictors in the trained model.</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-600"><Activity className="h-4 w-4" /> Model confidence</div>
                    <p className="text-sm text-slate-600">Random Forest model trained on 560k flights. ROC AUC: 0.66. Predicts 15+ minute delays.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="predictions">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm bg-card xl:col-span-8">
                <CardHeader>
                  <CardTitle>7-Day Delay Forecast</CardTitle>
                  <CardDescription>Actual vs predicted delay trends</CardDescription>
                </CardHeader>
                <CardContent className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.forecastData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#f9fafb", borderRadius: "8px", borderColor: "#e5e7eb" }}
                        itemStyle={{ color: "#1f2937" }}
                        labelStyle={{ color: "#6b7280", fontSize: "12px" }}
                      />
                      <Legend />
                      <Area type="monotone" dataKey="actual" stroke="#0f172a" fill="#cbd5e1" name="Recent Actual" />
                      <Area type="monotone" dataKey="predicted" stroke="#2563eb" fill="#93c5fd" name="Predicted" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
                <CardHeader>
                  <CardTitle>Run a Prediction</CardTitle>
                  <CardDescription>Enter flight details to get a real-time delay prediction</CardDescription>
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
                      {predicting ? "Predicting..." : "Run Prediction"}
                    </Button>
                    <Button variant="outline" className="rounded-xl" onClick={() => { setForm(EMPTY_FORM); setFieldErrors({}); setPredictionResult(null); setPredictionError(null); }}>
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
                          <p className="mb-2 text-xs font-medium text-slate-500">What influenced this prediction</p>
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
                </CardContent>
              </Card>
            </div>

            {history.length > 0 && (
              <Card className="mt-4 rounded-2xl border-none shadow-sm">
                <CardHeader>
                  <CardTitle>Prediction History</CardTitle>
                  <CardDescription>Last {history.length} predictions saved to database</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[800px] border-separate border-spacing-y-2">
                      <thead>
                        <tr className="text-left text-sm text-slate-500">
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
                          <tr key={p.id} className="bg-muted/20 text-sm">
                            <td className="rounded-l-xl px-4 py-3 font-medium text-foreground">{p.origin} → {p.destination}</td>
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
                            <td className="rounded-r-xl px-4 py-3 text-slate-400">{new Date(p.created_at).toLocaleTimeString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="flights">
            <Card className="rounded-2xl border-none shadow-sm">
              <CardHeader>
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <CardTitle>Flight Risk Table</CardTitle>
                    <CardDescription>Search and filter a flight-level prediction view</CardDescription>
                  </div>
                  <div className="grid w-full gap-3 md:grid-cols-2 xl:grid-cols-4 lg:w-auto">
                    <div className="relative min-w-[220px]">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search flight, route, airline" className="rounded-2xl pl-10" />
                    </div>
                    <Select value={airportFilter} onValueChange={setAirportFilter}>
                      <SelectTrigger className="rounded-2xl"><SelectValue placeholder="Airport" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Airports</SelectItem>
                        <SelectItem value="CLT">CLT</SelectItem>
                        <SelectItem value="ATL">ATL</SelectItem>
                        <SelectItem value="EWR">EWR</SelectItem>
                        <SelectItem value="DAL">DAL</SelectItem>
                        <SelectItem value="JFK">JFK</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select value={weatherFilter} onValueChange={setWeatherFilter}>
                      <SelectTrigger className="rounded-2xl"><SelectValue placeholder="Weather" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Weather</SelectItem>
                        <SelectItem value="Rain">Rain</SelectItem>
                        <SelectItem value="Storm">Storm</SelectItem>
                        <SelectItem value="Clear">Clear</SelectItem>
                        <SelectItem value="Wind">Wind</SelectItem>
                        <SelectItem value="Snow">Snow</SelectItem>
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
                <div className="mb-4 flex items-center gap-2 text-sm text-slate-500">
                  <Filter className="h-4 w-4" /> Showing {filteredFlights.length} flights for {dateRange}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px] border-separate border-spacing-y-3">
                    <thead>
                      <tr className="text-left text-sm text-slate-500">
                        <th className="px-4">Flight</th>
                        <th className="px-4">Route</th>
                        <th className="px-4">Airline</th>
                        <th className="px-4">Weather</th>
                        <th className="px-4">Predicted Delay</th>
                        <th className="px-4">Confidence</th>
                        <th className="px-4">Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFlights.map((flight) => (
                        <tr key={flight.id} className="rounded-2xl bg-slate-50 text-sm text-slate-600">
                          <td className="rounded-l-2xl px-4 py-4 font-semibold">{flight.id}</td>
                          <td className="px-4 py-4">{flight.route}</td>
                          <td className="px-4 py-4">{flight.airline}</td>
                          <td className="px-4 py-4">{flight.weather}</td>
                          <td className="px-4 py-4">{flight.predictedDelay} min</td>
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
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
