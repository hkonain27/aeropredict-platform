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
  Clock,
} from "lucide-react";
import { motion } from "framer-motion";

const IconMapping = {
  Plane: Plane,
  Clock3: Clock3,
  CloudRain: CloudRain,
  TrendingUp: TrendingUp,
};


const statusStyles = {
  "Low Risk": "bg-green-100 text-green-700 border-green-200",
  Moderate: "bg-yellow-100 text-yellow-700 border-yellow-200",
  "High Risk": "bg-orange-100 text-orange-700 border-orange-200",
  Critical: "bg-red-100 text-red-700 border-red-200",
};

const pieColors = ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"];

export default function App() {
  //
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://localhost:5001/api/dashboard-data");
        if(!response.ok) {
          throw new Error("Network response was not ok");
        }
        const data = await response.json();
        setData(data);
        setLoading(false);
      } catch (error) {
        console.error("Error fetching data:", error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);
  //


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

  if(loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <RefreshCcw className="animate-spin" />
      </div>
    );
  }

  //


  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
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
            <p className="mt-2 max-w-3xl text-sm text-slate-600 md:text-base">
              Monitor historic delay patterns, compare weather impact, and preview predictive analytics while the backend is still in progress.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" className="rounded-2xl">
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
            <Button className="rounded-2xl">Run Prediction</Button>
          </div>
        </motion.div>

        <Alert className="mb-6 rounded-2xl border-blue-200 bg-blue-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Frontend mode</AlertTitle>
          <AlertDescription>
            This version uses mock data and is structured so you can swap in live API responses later with minimal changes.
          </AlertDescription>
        </Alert>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.summaryCards.map((card, index) => {
            const Icon = card.icon;
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
                        <p className="text-sm text-slate-500">{card.title}</p>
                        <h2 className="mt-2 text-3xl font-semibold">{card.value}</h2>
                        <p className="mt-2 text-sm text-slate-500">
                          vs last period <span className="font-medium text-slate-700">{card.change}</span>
                        </p>
                      </div>
                      <div className="rounded-2xl bg-slate-100 p-3">
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
                  <Tooltip />
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
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-3 rounded-2xl bg-white p-1 shadow-sm md:w-[420px]">
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
                    <BarChart data={data.airportRiskData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="airport" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="risk" radius={[8, 8, 0, 0]} fill="#2563eb" />
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
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><MapPin className="h-4 w-4" /> Highest current risk</div>
                    <p className="text-sm text-slate-600">ORD and ATL show the strongest sustained delay risk in this mock analysis.</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><CloudRain className="h-4 w-4" /> Weather signal</div>
                    <p className="text-sm text-slate-600">Rain, storms, and snow are the strongest predictive features in this frontend placeholder.</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Activity className="h-4 w-4" /> Model confidence</div>
                    <p className="text-sm text-slate-600">Predictions above 85% confidence can be highlighted for operations and passenger alerts.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="predictions">
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
              <Card className="rounded-2xl border-none shadow-sm xl:col-span-8">
                <CardHeader>
                  <CardTitle>7-Day Delay Forecast</CardTitle>
                  <CardDescription>Prototype visualization for your predictive endpoint</CardDescription>
                </CardHeader>
                <CardContent className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.forecastData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="actual" stroke="#0f172a" fill="#cbd5e1" name="Recent Actual" />
                      <Area type="monotone" dataKey="predicted" stroke="#2563eb" fill="#93c5fd" name="Predicted" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="rounded-2xl border-none shadow-sm xl:col-span-4">
                <CardHeader>
                  <CardTitle>Model Status</CardTitle>
                  <CardDescription>Placeholder panel until backend model serving is ready</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span>Data pipeline readiness</span>
                      <span>74%</span>
                    </div>
                    <Progress value={74} className="h-3" />
                  </div>
                  <div>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span>Prediction service readiness</span>
                      <span>48%</span>
                    </div>
                    <Progress value={48} className="h-3" />
                  </div>
                  <Separator />
                  <div className="space-y-3 text-sm text-slate-600">
                    <p><strong>Next hookup:</strong> connect this panel to a <code>/health</code> or <code>/model/status</code> endpoint.</p>
                    <p><strong>Nice touch:</strong> show model version, last retrain date, and active feature set once your backend is live.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
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
                      <Input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search flight, route, airline"
                        className="rounded-2xl pl-10"
                      />
                    </div>

                    <Select value={airportFilter} onValueChange={setAirportFilter}>
                      <SelectTrigger className="rounded-2xl">
                        <SelectValue placeholder="Airport" />
                      </SelectTrigger>
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
                      <SelectTrigger className="rounded-2xl">
                        <SelectValue placeholder="Weather" />
                      </SelectTrigger>
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
                        <tr key={flight.id} className="rounded-2xl bg-slate-50 text-sm">
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