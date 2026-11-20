
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  MapPin,
  BriefcaseBusiness,
  Sparkles,
  ArrowUpRight,
  Code2,
  BrainCircuit,
  Database,
  Palette,
  Clock3,
  SlidersHorizontal,
  Bookmark,
  Zap,
  Menu,
  RefreshCw,
  AlertCircle,
  X,
  CheckCircle2
} from "lucide-react";

const API_URL = "http://127.0.0.1:8000";

const DEFAULT_CATEGORIES = [
  "Software Development",
  "AI / ML",
  "Data Analytics",
  "Design & Frontend"
];

function getCategoryIcon(name) {
  const value = name.toLowerCase();

  if (value.includes("ai") || value.includes("machine")) return BrainCircuit;
  if (value.includes("data")) return Database;
  if (value.includes("design") || value.includes("frontend")) return Palette;
  if (value.includes("software") || value.includes("development")) return Code2;

  return BriefcaseBusiness;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("All roles");
  const [type, setType] = useState("All");
  const [saved, setSaved] = useState([]);
  const [showSavedOnly, setShowSavedOnly] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);

  const [jobs, setJobs] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([
    "All roles",
    ...DEFAULT_CATEGORIES
  ]);
  const [stats, setStats] = useState({
    total_jobs: 0,
    verified_jobs: 0,
    cities: 0
  });

  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  async function loadData() {
    try {
      setLoading(true);
      setApiError("");

      const [jobsResponse, statsResponse, categoriesResponse] =
        await Promise.all([
          fetch(`${API_URL}/api/jobs?limit=200`),
          fetch(`${API_URL}/api/stats`),
          fetch(`${API_URL}/api/categories`)
        ]);

      if (!jobsResponse.ok || !statsResponse.ok) {
        throw new Error("Unable to retrieve data from the server.");
      }

      const jobsData = await jobsResponse.json();
      const statsData = await statsResponse.json();

      setJobs(jobsData.jobs || []);
      setStats(statsData);

      if (categoriesResponse.ok) {
        const categoriesData = await categoriesResponse.json();

        const categoryList = Array.isArray(categoriesData)
          ? categoriesData
          : categoriesData.categories || [];

        const names = categoryList
          .map((item) =>
            typeof item === "string"
              ? item
              : item.category || item.name
          )
          .filter(Boolean);

        setCategoryOptions([
          "All roles",
          ...new Set([...names, ...DEFAULT_CATEGORIES].filter((name) =>
            names.includes(name)
          ))
        ]);
      }

      setLastUpdated(new Date());
    } catch (error) {
      setApiError(
        "Cannot connect to the backend. Please make sure your Python server is running on port 8000."
      );
      console.error("API error:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const searchableText = [
        job.role,
        job.company,
        job.city,
        job.category,
        job.description
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch = searchableText.includes(
        query.trim().toLowerCase()
      );

      const matchesLocation = (job.city || "")
        .toLowerCase()
        .includes(location.trim().toLowerCase());

      const matchesCategory =
        category === "All roles" || job.category === category;

      const matchesType =
        type === "All" ||
        (job.job_type || "").toLowerCase() === type.toLowerCase();

      const matchesSaved =
        !showSavedOnly || saved.includes(job.id);

      return (
        matchesSearch &&
        matchesLocation &&
        matchesCategory &&
        matchesType &&
        matchesSaved
      );
    });
  }, [jobs, query, location, category, type, saved, showSavedOnly]);

  function clearFilters() {
    setQuery("");
    setLocation("");
    setCategory("All roles");
    setType("All");
    setShowSavedOnly(false);
  }

  function toggleSaved(jobId) {
    setSaved((previous) =>
      previous.includes(jobId)
        ? previous.filter((id) => id !== jobId)
        : [...previous, jobId]
    );
  }

  const categoryCards = categoryOptions.filter(
    (name) => name !== "All roles"
  );

  return (
    <div className="min-h-screen bg-[#090c18] text-white">

      {/* NAVBAR */}
      <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#090c18]/90 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">

          <a href="#" className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-500/20">
              <Zap size={22} fill="white" />
            </div>

            <span className="text-xl font-extrabold tracking-tight">
              FresherPulse<span className="text-violet-400">.</span>
            </span>
          </a>

          <div className="hidden items-center gap-8 text-sm text-slate-400 md:flex">
            <a href="#jobs" className="transition hover:text-white">Explore jobs</a>
            <a href="#categories" className="transition hover:text-white">Categories</a>
            <a href="#about" className="transition hover:text-white">About</a>
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
              <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Live database connection
            </span>
          </div>

          <button
            className="md:hidden"
            onClick={() => setMobileMenu(!mobileMenu)}
            aria-label="Toggle menu"
          >
            {mobileMenu ? <X /> : <Menu />}
          </button>
        </nav>

        {mobileMenu && (
          <div className="flex flex-col gap-4 border-t border-white/10 px-6 py-4 text-sm text-slate-300 md:hidden">
            <a href="#jobs" onClick={() => setMobileMenu(false)}>Explore jobs</a>
            <a href="#categories" onClick={() => setMobileMenu(false)}>Categories</a>
            <a href="#about" onClick={() => setMobileMenu(false)}>About</a>
          </div>
        )}
      </header>

      <main>

        {/* HERO */}
        <section className="relative overflow-hidden px-5 pb-16 pt-20 lg:pb-24 lg:pt-28">
          <div className="pointer-events-none absolute left-1/2 top-0 h-[450px] w-[750px] -translate-x-1/2 rounded-full bg-violet-700/20 blur-[130px]" />

          <div className="relative mx-auto max-w-5xl text-center">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8 inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-400/10 px-4 py-2 text-xs font-medium text-violet-300"
            >
              <Sparkles size={14} />
              Your next opportunity starts here
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl font-black leading-[1.12] tracking-tight sm:text-6xl lg:text-7xl"
            >
              Your career.
              <br />
              <span className="bg-gradient-to-r from-violet-400 via-fuchsia-300 to-indigo-400 bg-clip-text text-transparent">
                Your next move.
              </span>
            </motion.h1>

            <p className="mx-auto mt-6 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
              Discover fresher jobs and internships across India.
              Find opportunities that match your skills and ambitions.
            </p>

            {/* SEARCH */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mx-auto mt-10 grid max-w-4xl gap-2 rounded-2xl border border-white/10 bg-[#151a2a] p-2 shadow-2xl shadow-violet-950/30 sm:grid-cols-[1fr_0.7fr_auto]"
            >
              <div className="flex items-center gap-3 px-3">
                <Search className="shrink-0 text-violet-400" size={20} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Job title, skill or company..."
                  className="w-full bg-transparent py-3 text-sm outline-none placeholder:text-slate-500"
                />
              </div>

              <div className="flex items-center gap-3 border-t border-white/10 px-3 sm:border-l sm:border-t-0">
                <MapPin className="shrink-0 text-violet-400" size={20} />
                <input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="City or Remote"
                  className="w-full bg-transparent py-3 text-sm outline-none placeholder:text-slate-500"
                />
              </div>

              <button
                onClick={() => document.getElementById("jobs")?.scrollIntoView({ behavior: "smooth" })}
                className="rounded-xl bg-violet-600 px-7 py-3 text-sm font-bold transition hover:bg-violet-500"
              >
                Find jobs <ArrowUpRight className="ml-1 inline" size={16} />
              </button>
            </motion.div>

            <div className="mt-5 flex flex-wrap justify-center gap-2 text-xs text-slate-500">
              <span>Popular:</span>
              {["Python", "AI Engineer", "Data Analyst"].map((item) => (
                <button
                  key={item}
                  onClick={() => setQuery(item)}
                  className="rounded-full border border-white/10 px-3 py-1.5 transition hover:border-violet-400/40 hover:text-violet-300"
                >
                  {item}
                </button>
              ))}
              <button
                onClick={() => setLocation("Remote")}
                className="rounded-full border border-white/10 px-3 py-1.5 transition hover:border-violet-400/40 hover:text-violet-300"
              >
                Remote jobs
              </button>
            </div>
          </div>
        </section>

        {/* STATISTICS */}
        <section className="mx-auto grid max-w-6xl grid-cols-2 gap-3 px-5 pb-16 md:grid-cols-4">
          {[
            [stats.total_jobs ?? 0, "Total job listings"],
            [stats.verified_jobs ?? 0, "Verified listings"],
            [stats.cities ?? 0, "Cities covered"],
            ["Daily", "Planned update frequency"]
          ].map(([value, label]) => (
            <div key={label} className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
              <div className="text-2xl font-extrabold tracking-tight text-white">{value}</div>
              <div className="mt-1 text-xs text-slate-500">{label}</div>
            </div>
          ))}
        </section>

        {/* CATEGORIES */}
        <section id="categories" className="mx-auto max-w-7xl px-5 pb-14 lg:px-8">
          <div className="mb-6">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-400">Find your path</p>
            <h2 className="mt-2 text-2xl font-bold">Explore by category</h2>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {["All roles", ...categoryCards].map((name) => {
              const Icon = getCategoryIcon(name);

              return (
                <button
                  key={name}
                  onClick={() => setCategory(name)}
                  className={`flex min-h-24 flex-col items-start justify-between rounded-2xl border p-4 text-left transition ${
                    category === name
                      ? "border-violet-400/50 bg-violet-500/10"
                      : "border-white/[0.07] bg-white/[0.025] hover:border-violet-400/30"
                  }`}
                >
                  <Icon className="text-violet-400" size={22} />
                  <span className="text-xs font-semibold text-slate-200">{name}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* JOB BOARD */}
        <section id="jobs" className="mx-auto max-w-7xl px-5 pb-24 lg:px-8">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-400">Opportunity board</p>
              <h2 className="mt-2 text-2xl font-bold sm:text-3xl">Explore opportunities</h2>
              <p className="mt-2 text-sm text-slate-500">
                Job listings retrieved from the FresherPulse AI database.
              </p>
              {lastUpdated && (
                <p className="mt-1 text-xs text-slate-600">
                  Last refreshed: {lastUpdated.toLocaleTimeString()}
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
                <SlidersHorizontal size={15} />
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="ml-1 bg-transparent text-white outline-none"
                >
                  <option className="bg-[#151a2a]" value="All">All types</option>
                  <option className="bg-[#151a2a]" value="Internship">Internship</option>
                  <option className="bg-[#151a2a]" value="Full-time">Full-time</option>
                </select>
              </div>

              <button
                onClick={() => setShowSavedOnly(!showSavedOnly)}
                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs transition ${
                  showSavedOnly
                    ? "border-violet-400/40 bg-violet-500/20 text-violet-200"
                    : "border-white/10 text-slate-400 hover:text-white"
                }`}
              >
                <Bookmark size={14} />
                Saved ({saved.length})
              </button>

              <button
                onClick={loadData}
                disabled={loading}
                className="flex items-center gap-2 rounded-xl border border-violet-400/20 bg-violet-500/10 px-3 py-2 text-xs text-violet-300 transition hover:bg-violet-500/20 disabled:opacity-50"
              >
                <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                Refresh
              </button>
            </div>
          </div>

          <div className="mb-5 flex items-center justify-between text-xs text-slate-500">
            <span>{filteredJobs.length} opportunities found</span>
            <button onClick={clearFilters} className="hover:text-white">Clear all filters</button>
          </div>

          {loading && (
            <div className="rounded-2xl border border-white/10 py-16 text-center">
              <RefreshCw className="mx-auto mb-3 animate-spin text-violet-400" size={30} />
              <h3 className="font-semibold">Loading opportunities...</h3>
              <p className="mt-2 text-sm text-slate-500">Connecting to the job database.</p>
            </div>
          )}

          {!loading && apiError && (
            <div className="rounded-2xl border border-red-400/20 bg-red-400/5 py-12 text-center">
              <AlertCircle className="mx-auto mb-3 text-red-400" size={30} />
              <h3 className="font-semibold text-red-300">Backend connection problem</h3>
              <p className="mx-auto mt-2 max-w-lg px-4 text-sm text-slate-400">{apiError}</p>
              <button onClick={loadData} className="mt-5 rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold hover:bg-violet-500">
                Try again
              </button>
            </div>
          )}

          {!loading && !apiError && (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredJobs.map((job, i) => (
                <motion.article
                  key={job.id}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                  className="group rounded-2xl border border-white/[0.08] bg-[#111626] p-5 transition hover:-translate-y-1 hover:border-violet-400/30 hover:shadow-xl hover:shadow-violet-950/20"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/15 text-lg font-extrabold text-violet-300">
                        {job.company?.charAt(0).toUpperCase() || "?"}
                      </div>
                      <div>
                        <h3 className="font-bold text-white">{job.role}</h3>
                        <p className="mt-1 text-xs text-slate-500">{job.company}</p>
                      </div>
                    </div>

                    <button
                      onClick={() => toggleSaved(job.id)}
                      className={`rounded-lg p-2 transition ${
                        saved.includes(job.id)
                          ? "bg-violet-500/20 text-violet-300"
                          : "text-slate-500 hover:bg-white/5 hover:text-white"
                      }`}
                      title="Save job"
                    >
                      <Bookmark size={18} fill={saved.includes(job.id) ? "currentColor" : "none"} />
                    </button>
                  </div>

                  <div className="my-5 flex flex-wrap gap-2">
                    <span className="rounded-md bg-white/[0.06] px-2.5 py-1.5 text-xs text-slate-300">
                      <MapPin className="mr-1 inline" size={12} />
                      {job.city || "Location not specified"}
                    </span>
                    <span className="rounded-md bg-white/[0.06] px-2.5 py-1.5 text-xs text-slate-300">
                      <BriefcaseBusiness className="mr-1 inline" size={12} />
                      {job.job_type || "Not specified"}
                    </span>
                    <span className="rounded-md bg-white/[0.06] px-2.5 py-1.5 text-xs text-slate-300">
                      {job.category || "Unclassified"}
                    </span>
                  </div>

                  {job.description && (
                    <p className="mb-4 line-clamp-2 text-xs leading-6 text-slate-400">
                      {job.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between gap-3 border-t border-white/[0.07] pt-4">
                    <div>
                      <p className="text-sm font-bold text-slate-200">
                        {job.salary || "Salary not disclosed"}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        <Clock3 className="mr-1 inline" size={12} />
                        {job.posted_date || "Date not available"}
                      </p>
                    </div>

                    {job.apply_url ? (
                      <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="shrink-0 rounded-lg border border-violet-400/20 px-3 py-2 text-xs font-semibold text-violet-300 hover:bg-violet-500/10"
                      >
                        Apply now <ArrowUpRight className="ml-1 inline" size={13} />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500">No application link</span>
                    )}
                  </div>

                  {job.verified === 1 && (
                    <div className="mt-3 flex items-center gap-1 text-xs text-emerald-400">
                      <CheckCircle2 size={13} /> Verified listing
                    </div>
                  )}
                </motion.article>
              ))}

              {filteredJobs.length === 0 && (
                <div className="col-span-full rounded-2xl border border-white/10 py-16 text-center">
                  <Search className="mx-auto mb-3 text-slate-500" size={30} />
                  <h3 className="font-semibold">No matching opportunities</h3>
                  <p className="mt-2 text-sm text-slate-500">
                    No jobs are currently available for these filters. Try another keyword or clear your filters.
                  </p>
                  <button onClick={clearFilters} className="mt-5 rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold hover:bg-violet-500">
                    Clear filters
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      {/* FOOTER */}
      <footer id="about" className="border-t border-white/[0.07] px-5 py-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 text-xs text-slate-500 sm:flex-row">
          <span>© 2026 FresherPulse AI. Built for India's next generation.</span>
          <span>Discover opportunities. Build your future.</span>
        </div>
      </footer>
    </div>
  );
}
