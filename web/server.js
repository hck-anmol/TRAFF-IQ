const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const cors = require('cors');
const axios = require('axios'); // Make sure you have run 'npm install axios'

const app = express();
app.use(cors());
app.use(express.json());

// -------------------  IMPORTANT  -------------------
// PASTE YOUR OPENROUTESERVICE API KEY HERE
const ORS_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImM1OTQ5ZGU0M2M2NzQ0NDBiNDIwNTVlZmU0ZDhiNzBjIiwiaCI6Im11cm11cjY0In0=';
// ----------------------------------------------------

const server = http.createServer(app);

const io = new Server(server, {
    cors: {
        origin: "http://localhost:3000",
        methods: ["GET", "POST"]
    }
});

let networkState = {};

// --- API Endpoints ---

// This new endpoint gets routes from OpenRouteService
app.post('/api/route', async (req, res) => {
    const { start, end } = req.body; // e.g., start = [72.54, 23.03] (Lng, Lat)

    if (!start || !end) {
        return res.status(400).send('Start and end coordinates are required.');
    }

    try {
        const response = await axios.post(
            'https://api.openrouteservice.org/v2/directions/driving-car/geojson',
            {
                coordinates: [start, end],
                // Ask for alternative routes to show multiple options
                "alternative_routes": { "target_count": 3 }
            },
            {
                headers: {
                    'Authorization': ORS_API_KEY,
                    'Content-Type': 'application/json'
                }
            }
        );

        // Format the response for our Leaflet frontend
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


// Endpoint for your AI model data (no changes here)
app.post('/api/data', (req, res) => {
    networkState = req.body;
    io.emit('network_update', networkState);
    res.status(200).send({ status: 'Data received' });
});


// --- Socket.IO Connection ---
io.on('connection', (socket) => {
    console.log('✅ A React client connected.');
    socket.emit('network_update', networkState);
    socket.on('disconnect', () => {
        console.log('❌ A client disconnected.');
    });
});

const PORT = 5000;
server.listen(PORT, () => console.log(`🚀 Server is live and listening on http://localhost:${PORT}`));