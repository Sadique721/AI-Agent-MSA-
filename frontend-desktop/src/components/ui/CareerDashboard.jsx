/**
 * CareerDashboard.jsx  — V6→V10 Career OS Panel
 *
 * Renders live career intelligence metrics fetched from /api/career/*
 * Sections: Job Pipeline | ATS Scores | CRM Contacts | Analytics Funnel
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  Briefcase, Users, BarChart3, RefreshCw, CheckCircle,
  Clock, XCircle, TrendingUp, Mail, Target
} from 'lucide-react';

const API = 'http://localhost:5000';

const EMPTY_STATS = {
  funnel: { discovered: 0, applied: 0, interview: 0, offered: 0, rejected: 0 },
  response_rate: 0,
  total_applied: 0,
};

function StatCard({ icon: Icon, label, value, color = 'text-indigo-400', sub }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col gap-1 hover:bg-white/8 transition-all">
      <div className={`flex items-center gap-2 ${color}`}>
        <Icon size={16} />
        <span className="text-[10px] uppercase tracking-widest font-bold text-zinc-400">{label}</span>
      </div>
      <div className="text-2xl font-extrabold text-white">{value}</div>
      {sub && <div className="text-[10px] text-zinc-500">{sub}</div>}
    </div>
  );
}

function FunnelBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-[10px] text-zinc-400 text-right shrink-0">{label}</div>
      <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="w-8 text-[10px] text-zinc-300 font-mono">{value}</div>
    </div>
  );
}

export function CareerDashboard({ onClose }) {
  const [stats, setStats] = useState(EMPTY_STATS);
  const [contacts, setContacts] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('pipeline'); // pipeline | crm | analytics

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      // Analytics funnel
      const a = await fetch(`${API}/api/career/analytics`).then(r => r.ok ? r.json() : null);
      if (a) setStats(a);

      // Recent applications
      const j = await fetch(`${API}/api/career/applications`).then(r => r.ok ? r.json() : []);
      setJobs(Array.isArray(j) ? j.slice(0, 20) : []);

      // CRM contacts
      const c = await fetch(`${API}/api/career/crm/contacts`).then(r => r.ok ? r.json() : []);
      setContacts(Array.isArray(c) ? c.slice(0, 30) : []);
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const funnel = stats.funnel || EMPTY_STATS.funnel;
  const maxFunnel = Math.max(...Object.values(funnel), 1);

  const STATUS_STYLE = {
    discovered: 'text-zinc-400 bg-zinc-700/40',
    queued:     'text-yellow-300 bg-yellow-600/20',
    applied:    'text-blue-300 bg-blue-600/20',
    interview:  'text-emerald-300 bg-emerald-600/20',
    offered:    'text-violet-300 bg-violet-600/20',
    rejected:   'text-red-300 bg-red-600/20',
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-black/20">
        <div className="flex items-center gap-2">
          <Briefcase size={18} className="text-indigo-400" />
          <span className="text-sm font-bold tracking-wide">Career OS</span>
          <span className="text-[9px] uppercase tracking-widest text-zinc-500 border border-zinc-700 px-1.5 py-0.5 rounded-full">V6</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAll}
            className={`p-1.5 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-all ${loading ? 'animate-spin' : ''}`}
          >
            <RefreshCw size={14} />
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition-all text-xs">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Top stats row */}
      <div className="grid grid-cols-4 gap-3 px-5 pt-4 pb-2 shrink-0">
        <StatCard icon={Target}      label="Applied"    value={funnel.applied}    color="text-blue-400" />
        <StatCard icon={Clock}       label="Interview"  value={funnel.interview}  color="text-emerald-400" />
        <StatCard icon={CheckCircle} label="Offered"    value={funnel.offered}    color="text-violet-400" />
        <StatCard icon={TrendingUp}  label="Rate"       value={`${Math.round((stats.response_rate || 0) * 100)}%`} color="text-amber-400" sub="response rate" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-5 pb-3 pt-1 shrink-0">
        {[
          { id: 'pipeline', label: 'Job Pipeline', icon: Briefcase },
          { id: 'crm',      label: 'Recruiter CRM', icon: Users },
          { id: 'analytics',label: 'Funnel', icon: BarChart3 },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-semibold transition-all ${
              tab === id
                ? 'bg-indigo-600/30 text-white border border-indigo-500/50'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
            }`}
          >
            <Icon size={12} />{label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-5 pb-5">
        {tab === 'pipeline' && (
          <div className="flex flex-col gap-2">
            {jobs.length === 0 && (
              <div className="text-center text-zinc-600 text-sm py-16">
                No applications yet. Job discovery runs every hour in the background.
              </div>
            )}
            {jobs.map((job, i) => (
              <div key={job.job_id || i} className="bg-white/4 border border-white/8 rounded-xl p-3 flex items-center justify-between hover:bg-white/7 transition-all group">
                <div className="flex flex-col gap-0.5">
                  <div className="text-xs font-semibold text-zinc-100 group-hover:text-white">{job.title || job.job_id}</div>
                  <div className="text-[10px] text-zinc-500">{job.company} · {job.location}</div>
                  {job.ats_score > 0 && (
                    <div className="text-[9px] text-indigo-400 mt-0.5">ATS Score: {Math.round(job.ats_score * 100)}%</div>
                  )}
                </div>
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${STATUS_STYLE[job.status] || 'text-zinc-400 bg-zinc-700/30'}`}>
                  {job.status || 'discovered'}
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === 'crm' && (
          <div className="flex flex-col gap-2">
            {contacts.length === 0 && (
              <div className="text-center text-zinc-600 text-sm py-16">
                No recruiter contacts yet. Add contacts via the API.
              </div>
            )}
            {contacts.map((c, i) => (
              <div key={c.id || i} className="bg-white/4 border border-white/8 rounded-xl p-3 flex items-center justify-between hover:bg-white/7 transition-all">
                <div className="flex flex-col gap-0.5">
                  <div className="text-xs font-semibold text-zinc-100">{c.name}</div>
                  <div className="text-[10px] text-zinc-500">{c.company}</div>
                  {c.email && <div className="text-[9px] text-zinc-600">{c.email}</div>}
                </div>
                <div className="flex flex-col items-end gap-1">
                  {c.last_contacted && (
                    <span className="text-[9px] text-zinc-500">Last: {c.last_contacted.slice(0, 10)}</span>
                  )}
                  {c.email && (
                    <Mail size={12} className="text-zinc-600" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'analytics' && (
          <div className="flex flex-col gap-4 pt-2">
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Application Funnel</div>
            <div className="flex flex-col gap-3">
              <FunnelBar label="Discovered" value={funnel.discovered} max={maxFunnel} color="bg-zinc-500" />
              <FunnelBar label="Queued"     value={funnel.queued || 0} max={maxFunnel} color="bg-yellow-500" />
              <FunnelBar label="Applied"    value={funnel.applied}    max={maxFunnel} color="bg-blue-500" />
              <FunnelBar label="Interview"  value={funnel.interview}  max={maxFunnel} color="bg-emerald-500" />
              <FunnelBar label="Offered"    value={funnel.offered}    max={maxFunnel} color="bg-violet-500" />
              <FunnelBar label="Rejected"   value={funnel.rejected}   max={maxFunnel} color="bg-red-500" />
            </div>
            <div className="mt-4 p-4 bg-white/5 border border-white/10 rounded-2xl">
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Overall Response Rate</div>
              <div className="text-3xl font-extrabold text-white">
                {Math.round((stats.response_rate || 0) * 100)}<span className="text-lg text-zinc-400">%</span>
              </div>
              <div className="text-[10px] text-zinc-500 mt-1">{stats.total_applied || 0} total applications</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
