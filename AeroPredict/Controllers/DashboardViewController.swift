//
//  DashboardViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import UIKit

class DashboardViewController: UIViewController {

    @IBOutlet weak var trendsLabel: UILabel!
    @IBOutlet weak var airlinesLabel: UILabel!

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        loadDashboard()
    }

    private func loadDashboard() {
        let flights = StorageManager.shared.loadFlights()

        if flights.isEmpty {
            trendsLabel.text = """
            Delay Trends

            No saved flight data yet.
            Search and save flights to view trends.
            """

            airlinesLabel.text = """
            Risk Overview

            No saved flights available.
            """
            return
        }

        let high = flights.filter { $0.riskLevel == .high }.count
        let medium = flights.filter { $0.riskLevel == .medium }.count
        let low = flights.filter { $0.riskLevel == .low }.count
        let avgDelay = flights.map { $0.delayProbability }.reduce(0, +) / flights.count

        trendsLabel.text = """
        Delay Trends

        Saved Flights: \(flights.count)
        Average Delay Risk: \(avgDelay)%
        """

        airlinesLabel.text = """
        Risk Overview

        High Risk: \(high)
        Medium Risk: \(medium)
        Low Risk: \(low)
        """
    }
}
