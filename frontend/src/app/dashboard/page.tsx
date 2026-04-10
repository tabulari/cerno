'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { listIncidents, IncidentResponse } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    loadIncidents(filter);
  }, [filter]);

  async function loadIncidents(stateFilter: string) {
    setLoading(true);
    try {
      const data = await listIncidents(stateFilter || undefined);
      setIncidents(data);
    } catch (err) {
      console.error('Failed to load incidents:', err);
    } finally {
      setLoading(false);
    }
  }

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
    <ProtectedRoute>
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

          <div className="mb-6 flex gap-2 flex-wrap">
            <button
              onClick={() => setFilter('')}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === ''
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              All
            </button>
            {['SUBMITTED', 'TRIAGING', 'TRIAGED', 'TICKETED', 'NOTIFIED', 'RESOLVED'].map((state) => (
              <button
                key={state}
                onClick={() => setFilter(state)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  filter === state
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                {state}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-400">Loading...</div>
          ) : incidents.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              No incidents found
            </div>
          ) : (
            <div className="space-y-3">
              {incidents.map((incident) => (
                <Link
                  key={incident.id}
                  href={`/incidents/${incident.id}`}
                  className="block rounded-lg border border-gray-800 bg-gray-900/50 p-4 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-300">
                          #{incident.id}
                        </span>
                        {incident.triage_severity && (
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-semibold ${
                              severityColors[incident.triage_severity] || severityColors.P5
                            }`}
                          >
                            {incident.triage_severity}
                          </span>
                        )}
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-semibold ${
                            stateColors[incident.state] || stateColors.SUBMITTED
                          }`}
                        >
                          {incident.state}
                        </span>
                      </div>
                      <h3 className="text-base font-medium text-white truncate">
                        {incident.title}
                      </h3>
                      <p className="mt-1 text-sm text-gray-400 line-clamp-2">
                        {incident.description}
                      </p>
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
        </main>
      </div>
    </ProtectedRoute>
  );
}