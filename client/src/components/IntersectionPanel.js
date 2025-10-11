import React, { useState, useEffect } from 'react';

// A helper component for the traffic light display
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

    // This effect runs once to set up the timer
    useEffect(() => {
        // Simulate a random wait time at the red light
        const waitTime = Math.floor(Math.random() * 10) + 5; // Wait for 5-15 seconds
        setTimer(waitTime);
    }, [intersection]); // Reruns for each new intersection

    // This effect handles the countdown
    useEffect(() => {
        // If the timer is running, count down
        if (timer > 0) {
            const countdown = setTimeout(() => {
                setTimer(prev => prev - 1);
            }, 1000);
            return () => clearTimeout(countdown);
        } 
        // When the timer hits zero, it's our turn to go
        else if (timer === 0) {
            setMessage("SIGNAL IS GREEN! PROCEEDING...");
            // Wait 2 seconds on the green light, then tell the car to move
            const goTimeout = setTimeout(() => {
                onSignalGreen(); // This tells App.js to resume driving
            }, 2000);
            return () => clearTimeout(goTimeout);
        }
    }, [timer, onSignalGreen]);

    // Determine the light status based on the timer
    const ourSignalStatus = timer > 0 ? 'red' : 'green';
    const otherSignalStatus = timer > 0 ? 'green' : 'red';

    return (
        <div className="intersection-panel">
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