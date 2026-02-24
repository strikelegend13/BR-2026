const { spawn } = require('child_process');
const net = require('net');

function checkPort(port, name) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(2000);
    
    socket.on('connect', () => {
      console.log(`✅ ${name} is ready on port ${port}`);
      socket.destroy();
      resolve(true);
    });
    
    socket.on('timeout', () => {
      console.log(`⏳ Waiting for ${name} on port ${port}...`);
      socket.destroy();
      resolve(false);
    });
    
    socket.on('error', () => {
      console.log(`⏳ Waiting for ${name} on port ${port}...`);
      socket.destroy();
      resolve(false);
    });
    
    socket.connect(port, 'localhost');
  });
}

async function waitForServices() {
  console.log('Waiting for services to be ready...');
  
  let attempts = 0;
  const maxAttempts = 30;
  
  while (attempts < maxAttempts) {
    attempts++;
    console.log(`\n--- Attempt ${attempts}/${maxAttempts} ---`);
    
    const viteReady = await checkPort(3000, 'Vite Dev Server');
    const apiReady = await checkPort(5001, 'Python API');
    
    if (viteReady && apiReady) {
      console.log('All services ready! Starting Electron...');
      return true;
    }
    
    if (attempts >= maxAttempts) {
      console.log('Timeout waiting for services');
      return false;
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

async function startElectron() {
  const servicesReady = await waitForServices();
  
  if (!servicesReady) {
    console.log('Failed to start services. Please check:');
    console.log('1. Python API server is running: python3 api_server.py');
    console.log('2. Vite dev server is running: npm run start:renderer');
    process.exit(1);
  }
  
  console.log('Launching Electron app...');
  
  // Set environment variables for development
  const env = { ...process.env, NODE_ENV: 'development' };
  
  const electron = spawn('electron', ['.'], {
    stdio: 'inherit',
    shell: true,
    env: env
  });
  
  electron.on('close', (code) => {
    console.log(`Electron process exited with code ${code}`);
    process.exit(code);
  });
  
  electron.on('error', (error) => {
    console.error('Failed to start Electron:', error);
    process.exit(1);
  });
}

startElectron().catch(console.error); 
