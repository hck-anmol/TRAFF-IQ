const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const { spawn } = require('child_process');
const cors = require('cors');
const axios = require('axios');

const app = express();
app.use(cors());
app.use(express.json());

// -------------------  IMPORTANT  -------------------
// PASTE YOUR OPENROUTESERVICE API KEY HERE
const ORS_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImM1OTQ5ZGU0M2M2NzQ0NDBiNDIwNTVlZmU0ZDhiNzBjIiwiaCI6Im11cm11cjY0In0=';
// ----------------------------------------------------

// Add this near the top of server.js
const smartIntersections = {
    'navrangpura_crossing': {
        name: "Navrangpura Crossing",
        coords: [23.03994, 72.561204]
    },
    'subhash_bridge_east': {
        name: "Subhash Bridge East",
        coords: [23.061862, 72.594613]
    },
    'usmanpura_garden': {
        name: "Usmanpura Garden",
        coords: [23.052062, 72.565113]
    },
    'civil_hospital_area': {
        name: "Civil Hospital Area",
        coords: [23.067254, 72.600771]
    }
};

const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "http://localhost:3000",
        methods: ["GET", "POST"]
    }
});

const PORT = 5000;

// This object will store the running AI processes, mapping intersectionId to the process
const activeAIProcesses = {};

// --- API Endpoints ---

// 1. Get routes from OpenRouteService (your existing code, unchanged)
app.post('/api/route', async (req, res) => {
    const { start, end } = req.body;
    if (!start || !end) {
        return res.status(400).send('Start and end coordinates are required.');
    }
    try {
        const response = await axios.post(
            'https://api.openrouteservice.org/v2/directions/driving-car/geojson',
            {
                coordinates: [start, end],
                "alternative_routes": { "target_count": 3 }
            },
            {
                headers: {
                    'Authorization': ORS_API_KEY,
                    'Content-Type': 'application/json'
                }
            }
        );
        const routes = response.data.features.map((feature, index) => ({
            id: `route-${index}`,
            path: feature.geometry.coordinates.map(coord => [coord[1], coord[0]]), // Reverse to [Lat, Lng]
            summary: feature.properties.summary
        }));
        res.json(routes);
    } catch (error) {
        console.error('Error fetching from ORS:', error.response ? error.response.data : error.message);
        res.status(500).send('Error fetching routes');
    }
});

// 2. NEW: Get the optimal route using the AI snapshot
app.post('/api/optimal-route', (req, res) => {
    const { routes } = req.body;
    if (!routes || routes.length === 0) {
        return res.status(400).send('Routes data is required.');
    }

    console.log("🚀 Request received for optimal route. Running snapshot.py...");
    // Make sure your python command is correct, 'python' or 'python3'
    const snapshotProcess = spawn('python', ['../density/snapshot.py']);
    
    let snapshotData = '';
    snapshotProcess.stdout.on('data', (data) => {
        snapshotData += data.toString();
    });

    snapshotProcess.stderr.on('data', (data) => {
        console.error(`[SNAPSHOT_ERROR]: ${data}`);
    });

    snapshotProcess.on('close', (code) => {
        if (code === 0 && snapshotData) {
            console.log("✅ Snapshot complete. Calculating optimal route.");
            const densities = JSON.parse(snapshotData);
            
            // This is placeholder logic. In a real app, you would map intersections
            // to routes and calculate the one with the lowest total density.
            // For the demo, we'll just return the first route as optimal.
            const optimalRouteId = routes[0].id; 
            
            res.json({ optimalRouteId: optimalRouteId, densities: densities });
        } else {
            console.error(`Snapshot script exited with code ${code}`);
            res.status(500).json({ error: "Failed to generate traffic snapshot." });
        }
    });
});


// 3. Endpoint for the LIVE AI model to post its data to
app.post('/api/data', (req, res) => {
    const liveData = req.body;
    // Broadcast this live data to all connected clients with the correct event name
    io.emit('live_intersection_update', liveData);
    console.log(`📡 Broadcasted live data for ${liveData.intersectionId}`);
    res.status(200).send({ status: 'Data received and broadcasted' });
});


// --- Socket.IO for On-Demand AI Management ---
io.on('connection', (socket) => {
    console.log('✅ React client connected:', socket.id);

    // Listen for request from the frontend to START live analysis
    socket.on('startLiveAnalysis', ({ intersectionId }) => {
        if (!intersectionId) return;

        console.log(`▶️ Received request to START AI for: ${intersectionId}`);
        
        // If an AI process for this intersection isn't already running, start one
        if (!activeAIProcesses[intersectionId]) {
            // Using the unified 'final.py' script for live mode
            const aiProcess = spawn('python', ['../density/final.py', 'live', '--intersection_id', intersectionId]);
            activeAIProcesses[intersectionId] = aiProcess;

            // Log output and errors for debugging
            aiProcess.stdout.on('data', (data) => console.log(`[AI_LOG - ${intersectionId}]: ${data.toString().trim()}`));
            aiProcess.stderr.on('data', (data) => console.error(`[AI_ERROR - ${intersectionId}]: ${data.toString().trim()}`));
        }
    });

    // Listen for request from the frontend to STOP live analysis
    socket.on('stopLiveAnalysis', ({ intersectionId }) => {
        if (!intersectionId) return;

        console.log(`⏹️ Received request to STOP AI for: ${intersectionId}`);

        const process = activeAIProcesses[intersectionId];
        if (process) {
            process.kill('SIGTERM'); // Send termination signal
            delete activeAIProcesses[intersectionId];
            console.log(`   -> AI process for ${intersectionId} terminated.`);
        }
    });

    socket.on('disconnect', () => {
        console.log('❌ Client disconnected:', socket.id);
    });
});

server.listen(PORT, () => console.log(`🚀 Server is live and listening on http://localhost:${PORT}`));