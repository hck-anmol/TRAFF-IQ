import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
import L from 'leaflet';

import MapComponent from './components/MapComponent';
import RoutePlanner from './components/RoutePlanner';
import IntersectionPanel from './components/IntersectionPanel';
import Header from './components/Header';
import ExitFullScreenButton from './components/ExitFullScreenButton';
import './App.css';
import { goldenRoutes } from './mockRoutes';
// --- CONFIGURATION ---
const SERVER_URL = 'http://localhost:5000';
const socket = io(SERVER_URL);

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

function App() {
    const [viewMode, setViewMode] = useState('dashboard');
    const [routes, setRoutes] = useState([]);
    const [optimalRouteId, setOptimalRouteId] = useState(null);
    const [routesFound, setRoutesFound] = useState(false);
    const [message, setMessage] = useState('Find a route to begin.');
    const [driveStatus, setDriveStatus] = useState('stopped');
    const [carPosition, setCarPosition] = useState(null);
    const [currentIntersection, setCurrentIntersection] = useState(null);
    
    // NEW: State to hold the live data from the Python model
    const [liveIntersectionData, setLiveIntersectionData] = useState(null);

    // --- 1. FETCH REAL ROUTES FROM THE SERVER ---
    const findRoutes = async () => {
        setMessage('Fetching routes from server...');
        try {
            const startCoords = [72.557, 23.018]; // Lng, Lat
            const endCoords = [72.63, 23.13];   // Lng, Lat
            
            const response = await axios.post(`${SERVER_URL}/api/route`, {
                start: startCoords,
                end: endCoords,
            });

            // Reset visited status for a new journey
            Object.values(smartIntersections).forEach(int => int.visited = false);
            setRoutes(goldenRoutes);
            setRoutesFound(true);
            setMessage('Routes found! Now find the optimal one.');
        } catch (error) {
            console.error("Error fetching routes:", error);
            setMessage('Error: Could not fetch routes from the server.');
        }
    };

    // --- 2. GET REAL OPTIMAL ROUTE FROM THE AI SNAPSHOT ---
    const showOptimalAndDrive = async () => {
        if (!routesFound) return;
        setMessage('Running AI snapshot to find optimal route...');
        try {
            const response = await axios.post(`${SERVER_URL}/api/optimal-route`, { routes });
            setOptimalRouteId(response.data.optimalRouteId);
            setMessage(`Optimal route found! Starting journey...`);
            setDriveStatus('driving');
        } catch (error) {
            console.error("Error fetching optimal route:", error);
            setMessage('Error: Could not determine optimal route.');
        }
    };

    // --- 3. LISTEN FOR LIVE DATA FROM THE SERVER ---
    useEffect(() => {
        socket.on('live_intersection_update', (data) => {
            console.log("Received LIVE AI DATA:", data);
            if (currentIntersection && data.intersectionId === currentIntersection.id) {
                setLiveIntersectionData(data);
            }
        });

        return () => socket.off('live_intersection_update');
    }, [currentIntersection]); // Re-bind listener only when the intersection changes

    // --- 4. DRIVING SIMULATION WITH ON-DEMAND AI TRIGGERS ---
    useEffect(() => {
        if (driveStatus !== 'driving' || !optimalRouteId) return;

        const optimalRoute = routes.find(r => r.id === optimalRouteId);
        if (!optimalRoute) return;

        let currentIndex = carPosition
            ? optimalRoute.path.findIndex(p => p[0] === carPosition[0] && p[1] === carPosition[1])
            : 0;

        const interval = setInterval(() => {
            if (currentIndex >= optimalRoute.path.length - 1) {
                clearInterval(interval);
                setDriveStatus('stopped');
                setMessage('Journey Complete!');
                return;
            }

            currentIndex += 5; // Move faster between intersections
            const newPosition = optimalRoute.path[Math.min(currentIndex, optimalRoute.path.length - 1)];
            setCarPosition(newPosition);

            for (const id in smartIntersections) {
                const int = smartIntersections[id];
                if (int.visited) continue;

                const distance = L.latLng(newPosition).distanceTo(L.latLng(int.coords));
                if (distance < 200) { // Check from a further distance
                    int.visited = true;
                    const intersectionData = { id, ...int };
                    setCurrentIntersection(intersectionData);
                    setDriveStatus('stopped_at_signal');
                    
                    // Tell the server to START the AI for this intersection
                    console.log(`Approaching ${id}, sending startLiveAnalysis...`);
                    socket.emit('startLiveAnalysis', { intersectionId: id });

                    clearInterval(interval);
                    return;
                }
            }
        }, 150);

        return () => clearInterval(interval);
    }, [driveStatus, optimalRouteId, routes, carPosition]);
    
    // --- 5. HANDLE LEAVING THE INTERSECTION ---
    const handleSignalGreen = () => {
        if (currentIntersection) {
            // Tell the server to STOP the AI
            console.log(`Leaving ${currentIntersection.id}, sending stopLiveAnalysis...`);
            socket.emit('stopLiveAnalysis', { intersectionId: currentIntersection.id });
        }
        setCurrentIntersection(null);
        setLiveIntersectionData(null); // Clear live data
        setDriveStatus('driving'); // Resume driving
    };
    
    const toggleViewMode = () => setViewMode(prev => prev === 'dashboard' ? 'fullscreen' : 'dashboard');

    return (
        <div className={`app-container ${viewMode}-view`}>
            <div className="header-container">
                <Header onToggleView={toggleViewMode} viewMode={viewMode} />
            </div>
            <div className="main-content">
                <div className="sidebar">
                    <RoutePlanner
                        onFindRoutes={findRoutes}
                        onShowOptimal={showOptimalAndDrive}
                        routesFound={routesFound}
                        message={message}
                        viewMode={viewMode}
                    />
                </div>
                <div className="map-wrapper">
                    <MapComponent 
                        routes={routes}
                        optimalRouteId={optimalRouteId}
                        carPosition={carPosition}
                        smartIntersections={smartIntersections}
                    />
                </div>
            </div>
            
            {/* --- 6. PASS LIVE DATA TO THE PANEL --- */}
            {currentIntersection && 
                <IntersectionPanel 
                    intersection={currentIntersection} 
                    onSignalGreen={handleSignalGreen} 
                    liveData={liveIntersectionData} // <-- Pass the live data
                />
            }

            {viewMode === 'fullscreen' && <ExitFullScreenButton onClick={toggleViewMode} />}
        </div>
    );
}

export default App;