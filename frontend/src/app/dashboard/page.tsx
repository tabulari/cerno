'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { listIncidents, IncidentResponse } from '@/lib/api';
import Navbar from '@/components/Navbar';

function cn(...classes: (string | boolean | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [serviceFilter, setServiceFilter] = useState('');

  const loadIncidents = useCallback(async () => {
    try {
      const data = await listIncidents(filter || undefined);
      setIncidents(data);
    } catch (err) {
      console.error('Failed to load incidents:', err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadIncidents();
    const interval = setInterval(loadIncidents, 10000);
    return () => clearInterval(interval);
  }, [loadIncidents]);

  useEffect(() => {
    if (!loading && incidents.length === 0) {
      window.location.href = '/incidents/new';
    }
  }, [loading, incidents.length]);

  if (loading || incidents.length === 0) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  const filteredIncidents = incidents.filter((incident) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      incident.title.toLowerCase().includes(q) ||
      incident.description.toLowerCase().includes(q) ||
      incident.service.toLowerCase().includes(q)
    );
  });

  const services = Array.from(new Set(incidents.map((i) => i.service).filter(Boolean)));

  const stats = {
    total: incidents.length,
    open: incidents.filter((i) => ['SUBMITTED', 'TRIAGING', 'TRIAGED'].includes(i.state)).length,
    resolved: incidents.filter((i) => i.state === 'RESOLVED').length,
    p1: incidents.filter((i) => i.triage_severity === 'P1').length,
    p2: incidents.filter((i) => i.triage_severity === 'P2').length,
    p3: incidents.filter((i) => i.triage_severity === 'P3').length,
    p4: incidents.filter((i) => i.triage_severity === 'P4').length,
    p5: incidents.filter((i) => i.triage_severity === 'P5').length,
  };

  const severityColors: Record<string, string> = {
    P1: 'bg-red-500/20 text-red-400 border-red-500/30',
    P2: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    P3: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    P4: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    P5: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };

  const stateColors: Record<string, string> = {
    SUBMITTED: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    TRIAGING: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    TRIAGED: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    TICKETED: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    NOTIFIED: 'bg-green-500/20 text-green-400 border-green-500/30',
    RESOLVED: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    FAILED: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Incidents</h1>
          <Link
            href="/incidents/new"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            Report Incident
          </Link>
        </div>

        <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Total" value={stats.total} color="text-white" />
          <StatCard label="Open" value={stats.open} color="text-purple-400" />
          <StatCard label="Resolved" value={stats.resolved} color="text-emerald-400" />
          <StatCard label="P1" value={stats.p1} color="text-red-400" highlight={stats.p1 > 0} />
        </div>

        <div className="mb-6 flex gap-2 flex-wrap">
          {['P1', 'P2', 'P3', 'P4', 'P5'].map((sev) => (
            <div
              key={sev}
              className={cn('rounded-lg px-3 py-2 text-center min-w-[60px]', severityColors[sev])}
            >
              <div className="text-lg font-bold">{sev}</div>
              <div className="text-xs">{incidents.filter((i) => i.triage_severity === sev).length}</div>
            </div>
          ))}
        </div>

        <div className="mb-4 space-y-3">
          <input
            type="text"
            placeholder="Search incidents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          />

          <div className="flex flex-wrap gap-2">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All States</option>
              {['SUBMITTED', 'TRIAGING', 'TRIAGED', 'TICKETED', 'NOTIFIED', 'RESOLVED'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <select
              value={serviceFilter}
              onChange={(e) => setServiceFilter(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Services</option>
              {services.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            {(filter || serviceFilter || search) && (
              <button
                onClick={() => { setFilter(''); setServiceFilter(''); setSearch(''); }}
                className="text-sm text-gray-400 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {filteredIncidents.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            {search || filter || serviceFilter ? 'No matching incidents' : 'No incidents'}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredIncidents.map((incident) => (
              <Link
                key={incident.id}
                href={`/incidents/${incident.id}`}
                className="block rounded-lg border border-gray-800 bg-gray-900/50 p-4 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-300">#{incident.id}</span>
                      {incident.triage_severity && (
                        <span className={cn('rounded px-2 py-0.5 text-xs font-semibold', severityColors[incident.triage_severity] || severityColors.P5)}>
                          {incident.triage_severity}
                        </span>
                      )}
                      <span className={cn('rounded px-2 py-0.5 text-xs font-semibold', stateColors[incident.state] || stateColors.SUBMITTED)}>
                        {incident.state}
                      </span>
                    </div>
                    <h3 className="text-base font-medium text-white truncate">{incident.title}</h3>
                    <p className="mt-1 text-sm text-gray-400 line-clamp-2">{incident.description}</p>
                  </div>
                  <div className="text-right text-sm text-gray-500">
                    <div>{new Date(incident.created_at).toLocaleDateString()}</div>
                    <div>{incident.service}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="mt-4 text-center text-xs text-gray-600">Auto-refreshes every 10s</div>
      </main>
    </div>
  );
}

function StatCard({ label, value, color, highlight }: { label: string; value: number; color: string; highlight?: boolean }) {
  return (
    <div className={cn('rounded-lg border border-gray-800 bg-gray-900/50 p-4', highlight && 'border-red-500/50')}>
      <div className="text-2xl font-bold">{value}</div>
      <div className={cn('text-sm', color)}>{label}</div>
    </div>
  );
}