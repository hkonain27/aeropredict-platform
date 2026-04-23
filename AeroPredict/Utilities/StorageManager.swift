//
//  StorageManager.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import Foundation

final class StorageManager {
    static let shared = StorageManager()
    private init() {}

    private let savedFlightsKey = "savedFlights"

    func loadFlights() -> [FlightPrediction] {
        guard let data = UserDefaults.standard.data(forKey: savedFlightsKey) else { return [] }
        do {
            return try JSONDecoder().decode([FlightPrediction].self, from: data)
        } catch {
            return []
        }
    }

    func saveFlights(_ flights: [FlightPrediction]) {
        do {
            let data = try JSONEncoder().encode(flights)
            UserDefaults.standard.set(data, forKey: savedFlightsKey)
        } catch {
            print("Failed to save flights: \(error)")
        }
    }
}
