import React, { useState, useEffect } from 'react';

const TrafficLight = ({ status }) => (
    <div className="traffic-light">
        <div className={`light-circle red ${status === 'red' ? 'active' : ''}`}></div>
        <div className={`light-circle yellow ${status === 'yellow' ? 'active' : ''}`}></div>
        <div className={`light-circle green ${status === 'green' ? 'active' : ''}`}></div>
    </div>
);

const IntersectionPanel = ({ intersection, onSignalGreen }) => {
    const [timer, setTimer] = useState(0);
    const [message, setMessage] = useState("Waiting for signal...");
    const [emergency, setEmergency] = useState({ active: false, type: null });

    useEffect(() => {
        // Set the normal red light timer for ALL intersections
        const initialWaitTime = Math.floor(Math.random() * 10) + 8; // Wait 8-18 seconds
        setTimer(initialWaitTime);

        
        // Only schedule an emergency event if the intersection is enabled for it
        if (intersection.emergencyEnabled) {
            const emergencyTimeout = setTimeout(() => {
                const emergencyType = Math.random() > 0.5 ? 'clear_path' : 'hold_traffic';
                setEmergency({ active: true, type: emergencyType });

                if (emergencyType === 'clear_path') {
                    setMessage("EMERGENCY VEHICLE DETECTED! CLEARING YOUR PATH...");
                    setTimeout(() => onSignalGreen(), 2500);
                } else {
                    setMessage("EMERGENCY VEHICLE ON CROSS-STREET! HOLDING TRAFFIC...");
                    setTimer(10); // Hold for an extra 10 seconds
                }
            }, Math.random() * 5000 + 4000); // Emergency happens 4-9 seconds after stopping

            return () => clearTimeout(emergencyTimeout);
        }
    }, [intersection, onSignalGreen]);

    // This effect for the normal countdown timer remains the same
    useEffect(() => {
        if (timer > 0) {
            const countdown = setTimeout(() => setTimer(prev => prev - 1), 1000);
            return () => clearTimeout(countdown);
        } else if (timer === 0) {
            setMessage("SIGNAL IS GREEN! PROCEEDING...");
            const goTimeout = setTimeout(() => onSignalGreen(), 2000);
            return () => clearTimeout(goTimeout);
        }
    }, [timer, onSignalGreen]);

    // The rest of the component remains the same
    let ourSignalStatus = 'red';
    if (emergency.active && emergency.type === 'clear_path') {
        ourSignalStatus = 'green';
    } else if (timer === 0) {
        ourSignalStatus = 'green';
    }
    const otherSignalStatus = ourSignalStatus === 'green' ? 'red' : 'green';

    return (
        <div className={`intersection-panel ${emergency.active ? 'emergency-active' : ''}`}>
            {emergency.active && <div className="emergency-alert">⚠️ PRIORITY ALERT ⚠️</div>}
            <h3>Live at: {intersection.name}</h3>
            <div className="display-grid">
                <div className="light-column">
                    <h4>Your Signal</h4>
                    <TrafficLight status={ourSignalStatus} />
                </div>
                <div className="timer-column">
                    <div className="timer">{timer}s</div>
                    <p className="status-message">{message}</p>
                </div>
                <div className="light-column">
                    <h4>Cross Traffic</h4>
                    <TrafficLight status={otherSignalStatus} />
                </div>
            </div>
        </div>
    );
};

export default IntersectionPanel;