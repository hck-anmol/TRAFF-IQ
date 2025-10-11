import React, { useState, useEffect } from 'react';
import MapComponent from './components/MapComponent';
import RoutePlanner from './components/RoutePlanner';
import IntersectionPanel from './components/IntersectionPanel';
import './App.css';
import L from 'leaflet';
import { goldenRoutes } from './mockRoutes';

// --- FINAL INTERSECTION POINTS (MORE SPREAD OUT) ---
// These points are chosen from earlier and later parts of your saved routes
// to give a better-paced demonstration.
const smartIntersections = {
    // Points for Route 0
    'route0_int1': { 
        name: "Navrangpura Crossing", 
        coords: [23.040251, 72.567601] // Point from the first half of Route 0
    },
    'route0_int2': { 
        name: "Shahibag Underbridge", 
        coords: [23.071116, 72.603095] // Point from the second half of Route 0
    },
    // Points for Route 1
    'route1_int1': { 
        name: "Vadaj Circle", 
        coords: [23.055353, 72.571548] // Point from the first half of Route 1
    },
    'route1_int2': { 
        name: "Civil Hospital Area", 
        coords: [23.067254, 72.600771] // Point from the second half of Route 1
    }
};

function App() {
    const [routes, setRoutes] = useState([]);
    const [optimalRouteId, setOptimalRouteId] = useState(null);
    const [routesFound, setRoutesFound] = useState(false);
    const [message, setMessage] = useState('Welcome to the Traff-IQ Demo!');
    const [panelState, setPanelState] = useState('initial');
    
    const [driveStatus, setDriveStatus] = useState('stopped');
    const [carPosition, setCarPosition] = useState(null);
    const [currentIntersection, setCurrentIntersection] = useState(null);

    // NEW: This function just starts the demo and docks the panel
    const beginDemo = () => {
        setPanelState('docked');
        setMessage('Please select an option.');
    };

    // NEW: This function is now dedicated to showing the routes
    const displayRoutes = () => {
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
        <div className="App">
            <RoutePlanner
                onBeginDemo={beginDemo}
                onFindRoutes={displayRoutes} // Pass the new function
                onShowOptimal={showOptimalAndDrive}
                routesFound={routesFound}
                message={message}
                panelState={panelState}
            />
            {currentIntersection && 
                <IntersectionPanel 
                    intersection={currentIntersection} 
                    onSignalGreen={handleSignalGreen} 
                />
            }
            <MapComponent 
                routes={routes}
                optimalRouteId={optimalRouteId}
                carPosition={carPosition}
                smartIntersections={smartIntersections}
            />
        </div>
    );
}

// You will need to paste your 'showOptimalAndDrive', 'handleSignalGreen', and 'useEffect' code back in.
export default App;