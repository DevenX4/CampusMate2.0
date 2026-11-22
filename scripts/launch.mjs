// Starts, supervises and stops CampusMate's three local services.
//   node scripts/launch.mjs            start everything, open the browser when ready
//   node scripts/launch.mjs --no-open  same, without opening the browser
//   node scripts/launch.mjs --stop     stop a running copy
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HOST = '127.0.0.1';
const APP_URL = 'http://localhost:5173/';
const READY_TIMEOUT_MS = 180_000;
const WARMUP_TIMEOUT_MS = 120_000;
const MAX_RESTARTS = 5;
const STABLE_AFTER_MS = 60_000;
const LOW_MEMORY_GB = 2;
const PYTHON_MODULES = ['fastapi', 'uvicorn', 'chromadb', 'fastembed', 'psycopg', 'sqlalchemy', 'alembic',
    'pypdf', 'argon2', 'httpx', 'yaml', 'numpy', 'multipart', 'pydantic_settings'];

const SERVICES = [
    { name: 'AI', color: 35, port: 8010, command: 'python',
      args: ['-u', path.join(ROOT, 'AI_workflow', 'backend', 'run_server.py')],
      health: `http://${HOST}:8010/api/v1/system/health`, signature: `http://${HOST}:8010/openapi.json` },
    { name: 'NODE', color: 34, port: 5000, command: process.execPath,
      args: [path.join(ROOT, 'server', 'server.js')],
      health: `http://${HOST}:5000/api/health`, signature: `http://${HOST}:5000/` },
    { name: 'VITE', color: 36, port: 5173, command: process.execPath,
      args: [path.join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js')],
      health: `http://${HOST}:5173/src/main.jsx`, signature: `http://${HOST}:5173/` },
];

// A launcher started as "node scripts/launch.mjs" has no project path in its command line,
// so each run records its process id here for the next run or stop.bat to find it.
const PID_FILE = path.join(ROOT, 'node_modules', '.campusmate-launcher.pid');
const samePathText = (text) => text.toLowerCase().replaceAll('\\', '/');

function readRecordedPid() {
    try {
        return Number(readFileSync(PID_FILE, 'utf8').trim()) || 0;
    } catch {
        return 0;
    }
}

let stopping = false;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const say = (text) => console.log(`[CampusMate] ${text}`);

function powershell(script) {
    const result = spawnSync('powershell', ['-NoProfile', '-NonInteractive', '-Command', script],
        { encoding: 'utf8', windowsHide: true, maxBuffer: 4 * 1024 * 1024 });
    return (result.stdout || '').trim();
}

const killTree = (pid) => spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });

async function fetchText(url, timeoutMs = 2500) {
    try {
        const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
        return { ok: res.ok, text: await res.text() };
    } catch {
        return { ok: false, text: '' };
    }
}

function portIsOpen(port) {
    return new Promise((resolve) => {
        const socket = net.connect({ host: HOST, port });
        const finish = (open) => { socket.destroy(); resolve(open); };
        socket.setTimeout(700);
        socket.once('connect', () => finish(true));
        socket.once('timeout', () => finish(false));
        socket.once('error', () => finish(false));
    });
}

function portOwners() {
    const ports = SERVICES.map((s) => s.port).join(',');
    const output = powershell(`Get-NetTCPConnection -LocalPort ${ports} -State Listen -ErrorAction SilentlyContinue | `
        + `Sort-Object LocalPort,OwningProcess -Unique | ForEach-Object { `
        + `$p = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"; `
        + `"$($_.LocalPort)|$($_.OwningProcess)|$($p.Name)|$($p.CommandLine)" }`);
    return output.split(/\r?\n/).filter(Boolean).map((line) => {
        const [port, pid, name, ...rest] = line.split('|');
        return { port: Number(port), pid: Number(pid), name, commandLine: rest.join('|') };
    });
}

async function isCampusMate(owner) {
    if (samePathText(owner.commandLine).includes(samePathText(ROOT))) return true;
    const service = SERVICES.find((s) => s.port === owner.port);
    return (await fetchText(service.signature)).text.includes('CampusMate');
}

function stopOtherLaunchers() {
    const output = powershell(`Get-CimInstance Win32_Process -Filter "Name='node.exe'" | `
        + `Where-Object { $_.ProcessId -ne ${process.pid} -and $_.CommandLine -like '*launch.mjs*' `
        + `-and $_.CommandLine -notlike '*--stop*' } | ForEach-Object { `
        + `$parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"; `
        // Closing the old .bat window too, so it does not stay open showing a false "could not start".
        + `$target = if ($parent.Name -eq 'cmd.exe' -and $parent.CommandLine -like '*.bat*') { $parent.ProcessId } else { $_.ProcessId }; `
        + `"$target|$($_.ProcessId)|$($_.CommandLine)" }`);
    const recordedPid = readRecordedPid();
    for (const line of output.split(/\r?\n/).filter(Boolean)) {
        const [target, pid, ...rest] = line.split('|');
        if (Number(pid) === recordedPid || samePathText(rest.join('|')).includes(samePathText(ROOT))) killTree(target);
    }
}

// Only CampusMate's own processes are stopped. Anything else on these ports is reported and left alone.
async function clearPorts() {
    stopOtherLaunchers();
    const foreign = [];
    for (const owner of portOwners()) {
        if (await isCampusMate(owner)) killTree(owner.pid);
        else foreign.push(owner);
    }
    const foreignPorts = new Set(foreign.map((o) => o.port));
    const deadline = Date.now() + 10_000;
    while (Date.now() < deadline) {
        const open = await Promise.all(SERVICES.filter((s) => !foreignPorts.has(s.port)).map((s) => portIsOpen(s.port)));
        if (!open.some(Boolean)) break;
        await sleep(250);
    }
    return foreign;
}

function preflight() {
    if (!existsSync(path.join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js'))) {
        say('Installing website packages (first run only)...');
        const install = spawnSync('npm', ['install'], { cwd: ROOT, stdio: 'inherit', shell: true });
        if (install.status !== 0) {
            say('ERROR: npm install failed. Check your internet connection and run it again.');
            return false;
        }
    }

    const check = `import importlib.util as u; print(' '.join(m for m in ${JSON.stringify(PYTHON_MODULES)} if not u.find_spec(m)))`;
    const python = spawnSync('python', ['-c', check], { encoding: 'utf8', windowsHide: true });
    if (python.status !== 0) {
        say('ERROR: Python could not run. Install Python 3.11 or newer and add it to PATH.');
        return false;
    }
    const missing = python.stdout.trim();
    if (missing) {
        say(`ERROR: missing Python packages: ${missing}`);
        say('Fix: python -m pip install -e AI_workflow/backend');
        return false;
    }

    const freeKb = Number(powershell('(Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory'));
    if (freeKb && freeKb / 1024 / 1024 < LOW_MEMORY_GB) {
        const biggest = powershell('Get-Process | Group-Object ProcessName | ForEach-Object { [pscustomobject]@{ N = $_.Name; G = '
            + '(($_.Group | Measure-Object PrivateMemorySize64 -Sum).Sum / 1GB) } } | Sort-Object G -Descending | Select-Object -First 5 | '
            + 'ForEach-Object { "$($_.N) $([math]::Round($_.G, 1)) GB" }').split(/\r?\n/).join(', ');
        say(`WARNING: only ${(freeKb / 1024 / 1024).toFixed(1)} GB of memory is available. CampusMate needs about ${LOW_MEMORY_GB} GB.`);
        say(`Largest apps right now: ${biggest}. Close some of them if startup fails.`);
    }
    return true;
}

function startService(service) {
    const child = spawn(service.command, service.args, {
        cwd: ROOT,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8', NO_COLOR: '1' },
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
    });
    service.child = child;
    service.startedAt = Date.now();

    const prefix = `\x1b[${service.color}m[${service.name}]\x1b[0m`;
    for (const stream of [child.stdout, child.stderr]) {
        readline.createInterface({ input: stream }).on('line', (line) => console.log(`${prefix} ${line}`));
    }

    let ended = false;
    const onEnd = (reason) => {
        if (ended) return;
        ended = true;
        service.child = null;
        if (stopping) return;
        if (Date.now() - service.startedAt > STABLE_AFTER_MS) service.restarts = 0;
        service.restarts = (service.restarts || 0) + 1;
        // Never give up: on a busy PC a crash usually means memory was short, and memory comes back.
        const delay = service.restarts > MAX_RESTARTS ? 30_000 : Math.min(2000 * service.restarts, 15_000);
        if (service.restarts === MAX_RESTARTS + 1) {
            say(`WARNING: ${service.name} keeps stopping (${reason}). Close some apps to free memory. Retrying every 30s.`);
        } else if (service.restarts <= MAX_RESTARTS) {
            say(`${service.name} stopped (${reason}). Restarting in ${delay / 1000}s, attempt ${service.restarts}/${MAX_RESTARTS}...`);
        }
        setTimeout(() => { if (!stopping) startService(service); }, delay);
    };
    child.once('error', (err) => onEnd(err.message));
    child.once('exit', (code) => onEnd(`exit code ${code}`));
}

async function waitUntilHealthy(service, deadline) {
    while (Date.now() < deadline && !stopping) {
        if ((await fetchText(service.health)).ok) return true;
        await sleep(400);
    }
    return false;
}

// The first question loads the search models. Doing it here keeps the student's first question fast.
async function warmUpAnswerEngine() {
    try {
        // The local engine route: warming up must not spend the Groq quota.
        const res = await fetch(`http://${HOST}:8010/api/v1/chat/bypass`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: 'What is the minimum attendance requirement?' }),
            signal: AbortSignal.timeout(WARMUP_TIMEOUT_MS),
        });
        return res.ok;
    } catch {
        return false;
    }
}

function shutdown(code = 0) {
    if (stopping) return;
    stopping = true;
    for (const service of SERVICES) {
        if (service.child) killTree(service.child.pid);
    }
    if (readRecordedPid() === process.pid) rmSync(PID_FILE, { force: true });
    process.exit(code);
}

async function stopCommand() {
    const foreign = await clearPorts();
    rmSync(PID_FILE, { force: true });
    for (const owner of foreign) say(`Port ${owner.port} belongs to another program (${owner.name}), left running.`);
    say('All CampusMate services are stopped.');
}

async function main() {
    if (process.argv.includes('--stop')) return stopCommand();

    for (const signal of ['SIGINT', 'SIGTERM', 'SIGBREAK', 'SIGHUP']) process.on(signal, () => shutdown(0));

    if (!preflight()) process.exit(1);

    say('Clearing any previous CampusMate run...');
    const foreign = await clearPorts();
    if (foreign.length) {
        for (const owner of foreign) say(`ERROR: port ${owner.port} is used by another program: ${owner.name} (PID ${owner.pid}).`);
        say('Close that program and start CampusMate again. It was not stopped automatically.');
        process.exit(1);
    }

    writeFileSync(PID_FILE, String(process.pid));

    if (!(await portIsOpen(5432))) {
        say('WARNING: PostgreSQL is not running on port 5432. Start the postgresql service for database features.');
    }

    say('Starting services, the browser will open when they are ready...');
    // The website starts first, then the memory-heavy AI service, so they do not peak together.
    const [aiService, nodeService, viteService] = SERVICES;
    startService(nodeService);
    startService(viteService);

    const deadline = Date.now() + READY_TIMEOUT_MS;
    const [node, vite] = await Promise.all([nodeService, viteService].map((s) => waitUntilHealthy(s, deadline)));
    if (stopping) return;
    if (!node || !vite) {
        say(`ERROR: the website did not start (${!node ? 'NODE ' : ''}${!vite ? 'VITE' : ''}). See the messages above.`);
        shutdown(1);
        return;
    }

    startService(aiService);
    const ai = await waitUntilHealthy(aiService, deadline);
    if (stopping) return;

    let chatReady = false;
    if (ai) {
        say('Loading the answer engine...');
        chatReady = await warmUpAnswerEngine();
    }
    if (!chatReady) say('WARNING: the answer engine is not ready. The website will open, but chat answers are unavailable.');

    console.log('');
    say(`READY: ${APP_URL}`);
    say('Press Ctrl+C in this window to stop everything.');
    console.log('');
    if (!process.argv.includes('--no-open')) {
        spawn('cmd', ['/c', 'start', '', APP_URL], { stdio: 'ignore', detached: true, windowsHide: true }).unref();
    }
}

main().catch((err) => {
    console.error(err);
    shutdown(1);
});
