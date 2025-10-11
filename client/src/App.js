import React, { useState, useEffect } from 'react';
import MapComponent from './components/MapComponent';
import RoutePlanner from './components/RoutePlanner';
import IntersectionPanel from './components/IntersectionPanel';
import Header from './components/Header'; // <-- Import new component
import './App.css';
import L from 'leaflet';
import { goldenRoutes } from './mockRoutes';
import ExitFullScreenButton from './components/ExitFullScreenButton';

// --- FINAL INTERSECTION POINTS (MORE SPREAD OUT) ---
// These points are chosen from earlier and later parts of your saved routes
// to give a better-paced demonstration.

const smartIntersections = {
    'navrangpura_crossing': { 
        name: "Navrangpura Crossing", 
        coords: [23.03994, 72.561204],
        emergencyEnabled: true // This intersection can have emergencies
    },
    'subhash_bridge_east': { 
        name: "Subhash Bridge East", 
        coords: [23.061862, 72.594613],
        emergencyEnabled: false // This is a normal intersection
    },
    'usmanpura_garden': { 
        name: "Usmanpura Garden", 
        coords: [23.052062, 72.565113],
        emergencyEnabled: false // This is a normal intersection
    },
    'civil_hospital_area': { 
        name: "Civil Hospital Area", 
        coords: [23.067254, 72.600771],
        emergencyEnabled: true // This intersection can have emergencies
    }
};

function App() {
    // --- State Management ---
    const [viewMode, setViewMode] = useState('dashboard'); // 'dashboard' or 'fullscreen'
    const [routes, setRoutes] = useState([]);
    const [optimalRouteId, setOptimalRouteId] = useState(null);
    const [routesFound, setRoutesFound] = useState(false);
    const [message, setMessage] = useState('Welcome! Find a route to begin.');
    
    const [driveStatus, setDriveStatus] = useState('stopped');
    const [carPosition, setCarPosition] = useState(null);
    const [currentIntersection, setCurrentIntersection] = useState(null);

    // NEW: This function just starts the demo and docks the panel
    const toggleViewMode = () => {
        setViewMode(prev => prev === 'dashboard' ? 'fullscreen' : 'dashboard');
    };

    const findRoutes = () => {
        Object.values(smartIntersections).forEach(int => int.visited = false);
        setRoutes(goldenRoutes);
        setRoutesFound(true);
        setMessage('Routes found! Now find the optimal one.');
    };

    const showOptimalAndDrive = () => {
        if (!routesFound) return;
        
        let minDensity = Infinity;
        let bestRouteId = null;
        const routesWithDensity = routes.map(route => {
            const densityScore = Math.floor(Math.random() * 80) + 10;
            if (densityScore < minDensity) {
                minDensity = densityScore;
                bestRouteId = route.id;
            }
            return { ...route, densityScore };
        });
        
        setRoutes(routesWithDensity);
        setOptimalRouteId(bestRouteId);
        setMessage(`Optimal route found! Starting journey...`);
        setDriveStatus('driving');
    };

    const handleSignalGreen = () => {
        setCurrentIntersection(null);
        setDriveStatus('driving');
    };

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
            currentIndex++;
            const newPosition = optimalRoute.path[currentIndex];
            setCarPosition(newPosition);

            for (const id in smartIntersections) {
                const int = smartIntersections[id];
                if (int.visited) continue;

                const distance = L.latLng(newPosition).distanceTo(L.latLng(int.coords));
                if (distance < 100) {
                    int.visited = true;
                    setCurrentIntersection({ id, ...int });
                    setDriveStatus('stopped_at_signal');
                    clearInterval(interval);
                    return;
                }
            }
        }, 150); // <-- SLOWED DOWN: Changed from 80 to 150 for a slower demo

        return () => clearInterval(interval);
    }, [driveStatus, optimalRouteId, routes]);
    
   return (
        // The main container's class will now change dynamically
        <div className={`app-container ${viewMode}-view`}>
            {/* The header is only visible in dashboard mode */}
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
                        viewMode={viewMode} // Pass viewMode to control dragging
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
            
            {currentIntersection && 
                <IntersectionPanel 
                    intersection={currentIntersection} 
                    onSignalGreen={handleSignalGreen} 
                />
            }
            {/* NEW: Conditionally render the Exit button */}
            {viewMode === 'fullscreen' && <ExitFullScreenButton onClick={toggleViewMode} />}
        </div>
    );
}

// You will need to paste your existing functions (findRoutes, showOptimalAndDrive, etc.) back into this structure.
export default App;