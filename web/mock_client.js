// server/mock_client.js
const axios = require('axios');

const SERVER_URL = 'http://localhost:5000/api/data';

// These are the intersection IDs your frontend is expecting
const INTERSECTION_IDS = [
    'stadium_crossroads', 
    'hanuman_camp_road',
    'iskcon_crossroads', 
    'vaishnodevi_circle'
];

function generateRandomData() {
    const networkState = {};
    
    INTERSECTION_IDS.forEach(id => {
        // Create a random number of vehicles for each intersection
        networkState[id] = {
            total_vehicles: Math.floor(Math.random() * 80) + 5 // Random number between 5 and 85
        };
    });
    
    return networkState;
}

async function sendData() {
    const data = generateRandomData();
    try {
        await axios.post(SERVER_URL, data);
        console.log('✅ Sent mock data to server:', data);
    } catch (error) {
        console.error('❌ Error sending mock data:', error.message);
    }
}

// Send data every 3 seconds to simulate real-time updates
setInterval(sendData, 3000);

console.log('🚀 Mock client started. Sending data to server every 3 seconds...');