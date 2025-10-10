import React, { useState, useEffect } from 'react';

// The panel now accepts a function to call when its timer is done
const IntersectionPanel = ({ intersection, onSignalGreen }) => {
    const [densities, setDensities] = useState({});
    const [activeSignal, setActiveSignal] = useState('');
    const [timer, setTimer] = useState(0);

    // This effect simulates your AI logic (no changes here)
    useEffect(() => {
        const newDensities = {
            North: Math.floor(Math.random() * 50) + 5,
            South: Math.floor(Math.random() * 50) + 5,
            East: Math.floor(Math.random() * 50) + 5,
            West: Math.floor(Math.random() * 50) + 5,
        };
        setDensities(newDensities);

        const nsTraffic = newDensities.North + newDensities.South;
        const ewTraffic = newDensities.East + newDensities.West;
        
        const newActiveSignal = nsTraffic > ewTraffic ? 'North-South' : 'East-West';
        setActiveSignal(newActiveSignal);

        const newTime = Math.round(Math.max(nsTraffic, ewTraffic) / 3) + 10; // Shorter time for a quicker demo
        setTimer(newTime);
        
    }, [intersection]);

    // This effect is the countdown timer
    useEffect(() => {
        if (timer > 1) {
            const countdown = setInterval(() => setTimer(prev => prev - 1), 1000);
            return () => clearInterval(countdown);
        } else if (timer === 1) {
            // NEW: When the timer is about to hit zero, call the function
            const finalTimeout = setTimeout(() => {
                setTimer(0);
                onSignalGreen(); // Tell the App component the light is green!
            }, 1000);
            return () => clearTimeout(finalTimeout);
        }
    }, [timer, onSignalGreen]);

    return (
        <div className="intersection-panel">
            <h3>🔴 Live at: {intersection.name}</h3>
            <div className="density-display">
                <p>N: {densities.North}</p>
                <p>S: {densities.South}</p>
                <p>E: {densities.East}</p>
                <p>W: {densities.West}</p>
            </div>
            <div className="signal-status">
                <div className={`light ${activeSignal === 'North-South' ? 'green' : 'red'}`}>N-S</div>
                <div className="timer">{timer}s</div>
                <div className={`light ${activeSignal === 'East-West' ? 'green' : 'red'}`}>E-W</div>
            </div>
        </div>
    );
};

export default IntersectionPanel;