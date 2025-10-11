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

// --- Your Custom Icons ---
const carIcon = new L.Icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3202/3202926.png',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20]
});
const startIcon = new L.Icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3477/3477100.png',
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
});
const endIcon = new L.Icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3694/3694888.png',
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
});

// --- ADD THESE TWO MISSING LINES ---
// These are the coordinates from your goldenRoutes file
const startPosition = [23.034608, 72.5415]; 
const endPosition = [23.077529, 72.6275];
// ------------------------------------

const AHMEDABAD_CENTER = [23.05, 72.58];

const MapComponent = ({ routes, optimalRouteId, carPosition, smartIntersections }) => {
    return (
        <MapContainer center={AHMEDABAD_CENTER} zoom={13} style={{ height: '100vh', width: '100vw' }}>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            />
            
            <Marker position={startPosition} icon={startIcon}>
                <Popup><b>Start:</b> Hostel</Popup>
            </Marker>
            <Marker position={endPosition} icon={endIcon}>
                <Popup><b>End:</b> Airport</Popup>
            </Marker>

            {routes.map((route, index) => {
                const isOptimal = route.id === optimalRouteId;
                return (
                    <Polyline 
                        key={route.id} 
                        positions={route.path} 
                        pathOptions={{ 
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

            {smartIntersections && Object.entries(smartIntersections).map(([id, int]) => (
                <Marker key={id} position={int.coords}>
                    <Popup><b>Smart Intersection:</b> {int.name}</Popup>
                </Marker>
            ))}

            {carPosition && (
                <Marker position={carPosition} icon={carIcon}>
                    <Popup>Your Location</Popup>
                </Marker>
            )}
        </MapContainer>
    );
};

export default MapComponent;