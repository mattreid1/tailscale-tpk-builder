<?php
/**
 * Tailscale TOS5 API
 * JSON API for the React frontend
 */

header('Content-Type: application/json');

// Constants
define('MODULE_NAME', 'Tailscale');
define('RC_SCRIPT', '/etc/init.d/' . MODULE_NAME);
define('TAILSCALE_BIN', '/usr/local/' . MODULE_NAME . '/bin/program/tailscale');
define('LOG_DIR', '/usr/local/' . MODULE_NAME . '/config');

// Authentication check
session_start();
if (!((isset($_SESSION['kod_user']['role']) && $_SESSION['kod_user']['role'] === 'root') ||
      (isset($_SESSION['muser']) && $_SESSION['muser'] === 'admin'))) {
    echo json_encode(['success' => false, 'error' => 'Access denied']);
    exit;
}

// Get action from request
$action = isset($_GET['action']) ? $_GET['action'] : '';

// Route to handler
switch ($action) {
    case 'status':
        handleStatus();
        break;
    case 'service_status':
        handleServiceStatus();
        break;
    case 'autostart_status':
        handleAutostartStatus();
        break;
    case 'version':
        handleVersion();
        break;
    case 'start':
        handleStart();
        break;
    case 'stop':
        handleStop();
        break;
    case 'restart':
        handleRestart();
        break;
    case 'autostart_enable':
        handleAutostartEnable();
        break;
    case 'autostart_disable':
        handleAutostartDisable();
        break;
    case 'exit_node_enable':
        handleExitNodeEnable();
        break;
    case 'exit_node_disable':
        handleExitNodeDisable();
        break;
    case 'logs':
        handleLogs();
        break;
    case 'reset':
        handleReset();
        break;
    default:
        echo json_encode(['success' => false, 'error' => 'Invalid action']);
}

/**
 * Get Tailscale status JSON
 */
function handleStatus() {
    $output = shell_exec(TAILSCALE_BIN . ' status --json 2>&1');
    $data = json_decode($output, true);

    if ($data) {
        echo json_encode(['success' => true, 'data' => $data]);
    } else {
        // Try to parse error or return raw output
        echo json_encode(['success' => false, 'error' => $output ?: 'Unable to get status']);
    }
}

/**
 * Get service running status
 */
function handleServiceStatus() {
    $output = shell_exec(RC_SCRIPT . ' status 2>&1');
    $running = strpos($output, 'is running') !== false;
    $pid = null;

    if ($running && preg_match('/pid (\d+)/', $output, $matches)) {
        $pid = (int)$matches[1];
    }

    echo json_encode([
        'success' => true,
        'data' => [
            'running' => $running,
            'pid' => $pid,
            'message' => trim($output)
        ]
    ]);
}

/**
 * Get autostart status
 */
function handleAutostartStatus() {
    $output = shell_exec(RC_SCRIPT . ' status_autostart 2>&1');
    $enabled = strpos($output, 'Enabled') !== false;

    echo json_encode([
        'success' => true,
        'data' => ['enabled' => $enabled]
    ]);
}

/**
 * Get installed version
 */
function handleVersion() {
    $output = shell_exec(RC_SCRIPT . ' inst_version 2>&1');
    $version = '';

    if (preg_match('/(\d+\.\d+\.\d+(\.\d+)?)/', $output, $matches)) {
        $version = $matches[1];
    }

    echo json_encode([
        'success' => true,
        'data' => ['version' => $version]
    ]);
}

/**
 * Start service
 */
function handleStart() {
    $output = shell_exec(RC_SCRIPT . ' start 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}

/**
 * Stop service
 */
function handleStop() {
    $output = shell_exec(RC_SCRIPT . ' stop 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}

/**
 * Restart service
 */
function handleRestart() {
    $output = shell_exec(RC_SCRIPT . ' reload 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}

/**
 * Enable autostart
 */
function handleAutostartEnable() {
    $output = shell_exec(RC_SCRIPT . ' enable_autostart 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}

/**
 * Disable autostart
 */
function handleAutostartDisable() {
    $output = shell_exec(RC_SCRIPT . ' disable_autostart 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}

/**
 * Enable exit node
 */
function handleExitNodeEnable() {
    $output = shell_exec(TAILSCALE_BIN . ' set --advertise-exit-node 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output) ?: 'Exit node enabled']
    ]);
}

/**
 * Disable exit node
 */
function handleExitNodeDisable() {
    $output = shell_exec(TAILSCALE_BIN . ' set --advertise-exit-node=false 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output) ?: 'Exit node disabled']
    ]);
}

/**
 * Get logs
 */
function handleLogs() {
    $type = isset($_GET['type']) ? $_GET['type'] : 'startup';

    switch ($type) {
        case 'daemon':
            $file = LOG_DIR . '/tailscaled.log.conf';
            break;
        case 'startup':
        default:
            $file = LOG_DIR . '/Tailscale_start.log';
            break;
    }

    if (file_exists($file)) {
        // Read last 500 lines to avoid huge responses
        $lines = file($file);
        $content = implode('', array_slice($lines, -500));
        echo json_encode([
            'success' => true,
            'data' => ['content' => $content]
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error' => 'Log file not found'
        ]);
    }
}

/**
 * Reset configuration
 */
function handleReset() {
    $output = shell_exec(RC_SCRIPT . ' remove 2>&1');
    echo json_encode([
        'success' => true,
        'data' => ['message' => trim($output)]
    ]);
}
