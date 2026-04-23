//
//  SavedFlightsViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
//
//  SavedFlightsViewController.swift
//  AeroPredict
//

import UIKit

class SavedFlightsViewController: UIViewController, UITableViewDataSource, UITableViewDelegate {

    @IBOutlet weak var tableView: UITableView!
    @IBOutlet weak var emptyLabel: UILabel!

    var savedFlights: [FlightPrediction] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Saved Flights"
        tableView.dataSource = self
        tableView.delegate = self

        savedFlights = StorageManager.shared.loadFlights()
        emptyLabel.isHidden = !savedFlights.isEmpty
        tableView.reloadData()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        savedFlights = StorageManager.shared.loadFlights()
        emptyLabel.isHidden = !savedFlights.isEmpty
        tableView.reloadData()
    }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return savedFlights.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "SavedCell")
            ?? UITableViewCell(style: .subtitle, reuseIdentifier: "SavedCell")

        let flight = savedFlights[indexPath.row]
        cell.textLabel?.text = "\(flight.flightNumber)  \(flight.origin) → \(flight.destination)"
        cell.detailTextLabel?.text = "Delay: \(flight.delayProbability)%  •  Risk: \(flight.riskLevel.rawValue)"
        cell.selectionStyle = .none
        return cell
    }

    func tableView(_ tableView: UITableView, commit editingStyle: UITableViewCell.EditingStyle, forRowAt indexPath: IndexPath) {
        if editingStyle == .delete {
            savedFlights.remove(at: indexPath.row)
            tableView.deleteRows(at: [indexPath], with: .automatic)
            emptyLabel.isHidden = !savedFlights.isEmpty
            persistFlights()
        }
    }

    private func persistFlights() {
        StorageManager.shared.saveFlights(savedFlights)
    }
}
