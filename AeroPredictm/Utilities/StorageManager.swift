//
//  StorageManager.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import Foundation

class StorageManager {
    static let shared = StorageManager()
    private let key = "savedFlights"

    private init() {}

    func saveFlights(_ flights: [FlightPrediction]) {
        let encoder = JSONEncoder()
        if let data = try? encoder.encode(flights) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    func loadFlights() -> [FlightPrediction] {
        guard let data = UserDefaults.standard.data(forKey: key) else {
            return []
        }

        let decoder = JSONDecoder()
        return (try? decoder.decode([FlightPrediction].self, from: data)) ?? []
    }
}
