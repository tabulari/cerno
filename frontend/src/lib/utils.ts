export function severityColor(severity: string | null): string {
  switch (severity) {
    case 'P1': return 'text-red-500 bg-red-500/10 border-red-500/30';
    case 'P2': return 'text-orange-500 bg-orange-500/10 border-orange-500/30';
    case 'P3': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
    case 'P4': return 'text-blue-500 bg-blue-500/10 border-blue-500/30';
    case 'P5': return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    default: return 'text-gray-500 bg-gray-500/10 border-gray-500/30';
  }
}

export function stateColor(state: string): string {
  switch (state) {
    case 'SUBMITTED': return 'text-gray-400 bg-gray-400/10';
    case 'TRIAGING': return 'text-yellow-400 bg-yellow-400/10 animate-pulse';
    case 'TRIAGED': return 'text-blue-400 bg-blue-400/10';
    case 'TICKETED': return 'text-indigo-400 bg-indigo-400/10';
    case 'NOTIFIED': return 'text-green-400 bg-green-400/10';
    case 'RESOLVED': return 'text-emerald-400 bg-emerald-400/10';
    case 'FAILED': return 'text-red-400 bg-red-400/10';
    default: return 'text-gray-500 bg-gray-500/10';
  }
}

export function stateLabel(state: string): string {
  return state.charAt(0) + state.slice(1).toLowerCase();
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatDuration(ms: number | null): string {
  if (ms === null) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function agentIcon(agent: string): string {
  switch (agent) {
    case 'CodeAnalyst': return '{ }';
    case 'LogParser': return '::';
    case 'SeverityScorer': return '!#';
    case 'InstructorFallback': return '<<';
    default: return '>>';
  }
}
