import React from 'react';
import { MapContainer, TileLayer, Polyline, Popup, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// --- Fix for default marker icon ---
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
});

// A custom icon for our car
const carIcon = new L.Icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3202/3202926.png', // Example car icon
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20]
});

const AHMEDABAD_CENTER = [23.0225, 72.5714];

// The component accepts all props needed for the full simulation
const MapComponent = ({ routes, optimalRouteId, carPosition, smartIntersections }) => {
    return (
        <MapContainer center={AHMEDABAD_CENTER} zoom={12} style={{ height: '100vh', width: '100vw' }}>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            />
            
            {/* Logic to draw all fetched routes */}
            {routes.map((route, index) => {
                const isOptimal = route.id === optimalRouteId;
                return (
                    <Polyline 
                        key={route.id} 
                        positions={route.path} 
                        pathOptions={{ 
                            // High-contrast colors for better visibility
                            color: isOptimal ? '#ff006e' : '#03045e',
                            weight: isOptimal ? 10 : 7,
                            opacity: isOptimal ? 1.0 : 0.8
                        }}
                    >
                        <Popup>
                            <b>Route {index + 1}</b>
                            {route.densityScore && <><br/><b>Density: {route.densityScore}</b></>}
                            {isOptimal && <><br/><b>(OPTIMAL TRAFF-IQ ROUTE)</b></>}
                        </Popup>
                    </Polyline>
                );
            })}

            {/* Draw markers for the smart intersections */}
            {smartIntersections && Object.entries(smartIntersections).map(([id, int]) => (
                <Marker key={id} position={int.coords}>
                    <Popup><b>Smart Intersection:</b> {int.name}</Popup>
                </Marker>
            ))}

            {/* Draw the moving car marker during the simulation */}
            {carPosition && (
                <Marker position={carPosition} icon={carIcon}>
                    <Popup>Your Location</Popup>
                </Marker>
            )}
        </MapContainer>
    );
};

export default MapComponent;