// API wrapper for Tailscale TOS backend

export interface TailscaleStatus {
  BackendState: string;
  Self: {
    ID: string;
    HostName: string;
    DNSName: string;
    TailscaleIPs: string[];
    AllowedIPs?: string[];
    ExitNode?: boolean;
    ExitNodeOption?: boolean;
  };
  ExitNodeStatus?: {
    ID: string;
    Online: boolean;
    TailscaleIPs: string[];
  };
  Peer?: Record<string, {
    ID: string;
    HostName: string;
    DNSName: string;
    TailscaleIPs: string[];
    Online: boolean;
  }>;
  AuthURL?: string;
}

export interface ServiceStatus {
  running: boolean;
  pid?: number;
  message: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

const API_BASE = './api.php';

async function apiCall<T>(action: string): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}?action=${action}`);
    const data = await response.json();
    return data;
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

export const api = {
  // Tailscale status
  getStatus: () => apiCall<TailscaleStatus>('status'),

  // Service control
  getServiceStatus: () => apiCall<ServiceStatus>('service_status'),
  getAutostartStatus: () => apiCall<{ enabled: boolean }>('autostart_status'),
  getVersion: () => apiCall<{ version: string }>('version'),

  start: () => apiCall<{ message: string }>('start'),
  stop: () => apiCall<{ message: string }>('stop'),
  restart: () => apiCall<{ message: string }>('restart'),

  enableAutostart: () => apiCall<{ message: string }>('autostart_enable'),
  disableAutostart: () => apiCall<{ message: string }>('autostart_disable'),

  // Exit node
  enableExitNode: () => apiCall<{ message: string }>('exit_node_enable'),
  disableExitNode: () => apiCall<{ message: string }>('exit_node_disable'),

  // Logs
  getLogs: (type: 'daemon' | 'startup') => apiCall<{ content: string }>(`logs&type=${type}`),

  // Destructive
  reset: () => apiCall<{ message: string }>('reset'),
};
