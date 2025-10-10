import React, { useState, useEffect } from 'react';
import MapComponent from './components/MapComponent';
import RoutePlanner from './components/RoutePlanner';
import IntersectionPanel from './components/IntersectionPanel';
import './App.css';
import L from 'leaflet';
import { goldenRoutes } from './mockRoutes';

const smartIntersections = {
    'route0_int1': { name: "Navrangpura Crossing", coords: [23.03994, 72.561204] },
    'route0_int2': { name: "Subhash Bridge East", coords: [23.061862, 72.594613] },
    'route1_int1': { name: "Usmanpura Garden", coords: [23.052062, 72.565113] },
    'route1_int2': { name: "Dudheshwar Bridge", coords: [23.057584, 72.590991] }
};

function App() {
    const [routes, setRoutes] = useState([]);
    const [optimalRouteId, setOptimalRouteId] = useState(null);
    const [routesFound, setRoutesFound] = useState(false);
    const [message, setMessage] = useState('Click the button to begin the demo.');
    
    // This is the state that controls the car's movement.
    const [driveStatus, setDriveStatus] = useState('stopped'); // 'stopped', 'driving', 'stopped_at_signal'
    const [carPosition, setCarPosition] = useState(null);
    const [currentIntersection, setCurrentIntersection] = useState(null);

    const findRoutes = () => {
        // Reset intersections before finding new routes
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
        setDriveStatus('driving'); // Correctly start the journey
    };

    // This function is called by the panel when the light turns green
    const handleSignalGreen = () => {
        setCurrentIntersection(null);
        setDriveStatus('driving');
    };

    // This effect runs the driving simulation
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

            // Proximity Detection Logic
            for (const id in smartIntersections) {
                const int = smartIntersections[id];
                // Ensure the car hasn't already visited this intersection
                if (int.visited) continue;

                const distance = L.latLng(newPosition).distanceTo(L.latLng(int.coords));
                if (distance < 100) {
                    int.visited = true; // Mark as visited to prevent re-triggering
                    setCurrentIntersection({ id, ...int });
                    setDriveStatus('stopped_at_signal');
                    clearInterval(interval);
                    return;
                }
            }
        }, 80);

        return () => clearInterval(interval);
    }, [driveStatus, optimalRouteId, routes]);
    
    return (
        <div className="App">
            <RoutePlanner
                onFindRoutes={findRoutes}
                onShowOptimal={showOptimalAndDrive}
                routesFound={routesFound}
                message={message}
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

export default App;