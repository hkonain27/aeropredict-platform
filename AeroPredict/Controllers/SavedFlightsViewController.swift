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
           setupView()
           setupTableView()
           setupEmptyLabel()
           loadSavedFlights()
       }

       override func viewWillAppear(_ animated: Bool) {
           super.viewWillAppear(animated)
           loadSavedFlights()
       }

       private func setupView() {
           view.backgroundColor = UIColor.systemGray6
           tableView.backgroundColor = .clear
       }

       private func setupTableView() {
           tableView.dataSource = self
           tableView.delegate = self
           tableView.separatorStyle = .none
           tableView.rowHeight = 110
           tableView.showsVerticalScrollIndicator = false
           tableView.contentInset = UIEdgeInsets(top: 8, left: 0, bottom: 20, right: 0)
       }

       private func setupEmptyLabel() {
           emptyLabel.text = "No saved flights yet"
           emptyLabel.textColor = .secondaryLabel
           emptyLabel.font = UIFont.systemFont(ofSize: 18, weight: .medium)
           emptyLabel.textAlignment = .center
           emptyLabel.numberOfLines = 0
       }

       private func loadSavedFlights() {
           savedFlights = StorageManager.shared.loadFlights()
           emptyLabel.isHidden = !savedFlights.isEmpty
           tableView.reloadData()
       }

       func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
           return savedFlights.count
       }

       func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
           let flight = savedFlights[indexPath.row]
           let cell = tableView.dequeueReusableCell(withIdentifier: "SavedCell")
               ?? UITableViewCell(style: .subtitle, reuseIdentifier: "SavedCell")

           var content = UIListContentConfiguration.subtitleCell()
           content.text = "\(flight.flightNumber)   \(flight.origin) → \(flight.destination)"
           content.secondaryText = "Delay: \(flight.delayProbability)%   Risk: \(flight.riskLevel.rawValue)"
           content.textProperties.font = UIFont.systemFont(ofSize: 18, weight: .bold)
           content.secondaryTextProperties.font = UIFont.systemFont(ofSize: 16, weight: .semibold)

           switch flight.riskLevel {
           case .low:
               content.secondaryTextProperties.color = .systemGreen
           case .medium:
               content.secondaryTextProperties.color = .systemOrange
           case .high:
               content.secondaryTextProperties.color = .systemRed
           }

           cell.contentConfiguration = content
           cell.selectionStyle = .none
           cell.backgroundColor = .white
           cell.layer.cornerRadius = 22
           cell.layer.masksToBounds = false
           cell.layer.shadowColor = UIColor.black.cgColor
           cell.layer.shadowOpacity = 0.06
           cell.layer.shadowOffset = CGSize(width: 0, height: 6)
           cell.layer.shadowRadius = 12

           return cell
       }

       func tableView(_ tableView: UITableView, canEditRowAt indexPath: IndexPath) -> Bool {
           return true
       }

       func tableView(_ tableView: UITableView,
                      commit editingStyle: UITableViewCell.EditingStyle,
                      forRowAt indexPath: IndexPath) {
           if editingStyle == .delete {
               savedFlights.remove(at: indexPath.row)
               persistFlights()
               loadSavedFlights()
           }
       }

       private func persistFlights() {
           StorageManager.shared.saveFlights(savedFlights)
       }
   }

