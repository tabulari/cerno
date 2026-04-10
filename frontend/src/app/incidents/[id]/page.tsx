'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  getIncident,
  getTransitions,
  IncidentResponse,
  StateTransition,
} from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';

const SEVERITY_COLORS: Record<string, string> = {
  P1: 'bg-red-600 text-white',
  P2: 'bg-orange-600 text-white',
  P3: 'bg-yellow-600 text-white',
  P4: 'bg-blue-600 text-white',
  P5: 'bg-gray-600 text-white',
};

const STATE_COLORS: Record<string, string> = {
  SUBMITTED: 'bg-gray-500 text-white',
  TRIAGING: 'bg-purple-500 text-white',
  TRIAGED: 'bg-blue-500 text-white',
  TICKETED: 'bg-indigo-500 text-white',
  NOTIFIED: 'bg-green-500 text-white',
  RESOLVED: 'bg-emerald-500 text-white',
  FAILED: 'bg-red-500 text-white',
};

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [incident, setIncident] = useState<IncidentResponse | null>(null);
  const [transitions, setTransitions] = useState<StateTransition[]>([]);
  const [loading, setLoading] = useState(true);
  const [openSteps, setOpenSteps] = useState<Set<string>>(new Set());

  const loadData = useCallback(async () => {
    try {
      const [incidentData, transitionsData] = await Promise.all([
        getIncident(id),
        getTransitions(id).catch(() => [] as StateTransition[]),
      ]);
      setIncident(incidentData);
      setTransitions(transitionsData);
    } catch (err) {
      console.error('Failed to load incident:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!id || isNaN(id)) {
      router.push('/dashboard');
      return;
    }
    loadData();
  }, [id, loadData, router]);

  useEffect(() => {
    if (!incident || !['SUBMITTED', 'TRIAGING'].includes(incident.state)) return;

    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [incident?.state, loadData]);

  function toggleStep(agent: string) {
    const next = new Set(openSteps);
    if (next.has(agent)) {
      next.delete(agent);
    } else {
      next.add(agent);
    }
    setOpenSteps(next);
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gray-950 text-white">
          <Navbar />
          <div className="flex items-center justify-center py-20">
            <span className="text-gray-400">Loading incident...</span>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (!incident) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gray-950 text-white">
          <Navbar />
          <div className="mx-auto max-w-2xl px-4 py-20 text-center">
            <h1 className="text-2xl font-bold mb-4">Incident not found</h1>
            <Link href="/dashboard" className="text-indigo-400 hover:text-indigo-300">
              Back to dashboard
            </Link>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  const reasoningSteps = incident.reasoning_steps || [];
  const finalState = incident.state;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-950 text-white">
        <Navbar />
        <main className="mx-auto max-w-4xl px-4 py-8">
          <div className="mb-6">
            <Link
              href="/dashboard"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              ← Back to Dashboard
            </Link>
          </div>

          {/* Header */}
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 mb-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl font-bold text-gray-300">#{incident.id}</span>
                  {incident.triage_severity && (
                    <span
                      className={`rounded px-3 py-1 text-sm font-bold ${
                        SEVERITY_COLORS[incident.triage_severity] || SEVERITY_COLORS.P5
                      }`}
                    >
                      {incident.triage_severity}
                    </span>
                  )}
                  <span
                    className={`rounded px-3 py-1 text-sm font-semibold ${
                      STATE_COLORS[finalState] || STATE_COLORS.SUBMITTED
                    }`}
                  >
                    {finalState}
                  </span>
                  {incident.needs_human_review && (
                    <span className="rounded bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-3 py-1 text-sm font-semibold">
                      Needs Review
                    </span>
                  )}
                </div>
                <h1 className="text-xl font-semibold">{incident.title}</h1>
              </div>
              <div className="text-right text-sm text-gray-500">
                <div>{new Date(incident.created_at).toLocaleString()}</div>
                <div className="mt-1">Service: {incident.service}</div>
              </div>
            </div>

            <p className="text-gray-400 whitespace-pre-wrap">{incident.description}</p>

            {incident.confidence !== null && (
              <div className="mt-4 pt-4 border-t border-gray-800">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">AI Confidence:</span>
                  <div className="flex-1 max-w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                      style={{ width: `${(incident.confidence || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-300">
                    {Math.round((incident.confidence || 0) * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Timeline</h2>
            <div className="relative">
              <div className="absolute left-3.5 top-2 bottom-2 w-0.5 bg-gray-700" />
              {transitions.length === 0 ? (
                <div className="relative flex items-center gap-3 pl-9">
                  <div className="w-4 h-4 rounded-full bg-gray-600 border-2 border-gray-900 z-10" />
                  <div className="text-gray-400">Waiting for triage...</div>
                </div>
              ) : (
                transitions.map((t, i) => (
                  <div key={i} className="relative flex items-center gap-3 py-2">
                    <div
                      className={`w-4 h-4 rounded-full border-2 z-10 ${
                        i === transitions.length - 1
                          ? 'bg-indigo-500 border-gray-900'
                          : 'bg-green-500 border-gray-900'
                      }`}
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-300">
                          {t.to_state}
                        </span>
                        <span className="text-sm text-gray-500">
                          {t.duration_ms !== null && `${t.duration_ms}ms`}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(t.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Reasoning Accordion */}
          {reasoningSteps.length > 0 && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">AI Reasoning</h2>
              <div className="space-y-3">
                {reasoningSteps.map((step, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-gray-700 overflow-hidden"
                  >
                    <button
                      onClick={() => toggleStep(step.agent)}
                      className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-800 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-white">{step.agent}</span>
                        <span className="text-xs text-gray-500">{step.duration_ms}ms</span>
                      </div>
                      <span className="text-gray-400">
                        {openSteps.has(step.agent) ? '▼' : '▶'}
                      </span>
                    </button>
                    {openSteps.has(step.agent) && (
                      <div className="px-4 pb-4">
                        {step.tool_calls.length > 0 && (
                          <div className="mb-3">
                            <p className="text-xs text-gray-500 mb-1">Tool Calls</p>
                            <div className="space-y-1">
                              {step.tool_calls.map((tc, j) => (
                                <div
                                  key={j}
                                  className="text-xs font-mono text-gray-400 bg-gray-800 rounded px-2 py-1"
                                >
                                  {tc.name}: {tc.input} → {tc.output}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <p className="text-xs text-gray-500 mb-1">Finding</p>
                        <p className="text-sm text-gray-300 whitespace-pre-wrap">
                          {step.finding}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Triage Result */}
          {(incident.triage_summary || incident.triage_runbook) && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">Triage Result</h2>
              {incident.triage_summary && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 mb-1">Summary</p>
                  <p className="text-gray-300 whitespace-pre-wrap">
                    {incident.triage_summary}
                  </p>
                </div>
              )}
              {incident.triage_runbook && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Suggested Runbook</p>
                  <div className="rounded-lg bg-gray-800 px-4 py-3">
                    <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                      {incident.triage_runbook}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}