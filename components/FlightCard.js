import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function FlightCard({ flight, darkMode }) {
  const styles = StyleSheet.create({
    card: {
      padding: 15,
      marginVertical: 8,
      borderRadius: 10,
      backgroundColor: flight.status.toLowerCase().includes('delayed') ? (darkMode ? '#c62828' : '#f8d7da') : (darkMode ? '#2e7d32' : '#d4edda'),
    },
    flightNumber: { fontSize: 18, fontWeight: '600', color: darkMode ? '#fff' : '#000' },
    flightStatus: { fontSize: 16, marginTop: 5, color: darkMode ? '#fff' : '#000' },
    flightInfo: { fontSize: 14, marginTop: 2, color: darkMode ? '#fff' : '#000' },
  });

  return (
    <View style={styles.card}>
      <Text style={styles.flightNumber}>{flight.number}</Text>
      <Text style={styles.flightStatus}>{flight.status}</Text>
      <Text style={styles.flightInfo}>From: {flight.departure}</Text>
      <Text style={styles.flightInfo}>To: {flight.arrival}</Text>
      <Text style={styles.flightInfo}>Departure: {flight.scheduled}</Text>
    </View>
  );
}
