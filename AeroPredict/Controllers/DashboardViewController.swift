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
    @IBOutlet weak var trendsCardView: UIView!
    @IBOutlet weak var riskCardView: UIView!
    override func viewDidLoad() {
            super.viewDidLoad()
            title = "Dashboard"
            setupView()
            setupCards()
            setupLabels()
        }

        override func viewWillAppear(_ animated: Bool) {
            super.viewWillAppear(animated)
            loadDashboard()
        }

        private func setupView() {
            view.backgroundColor = UIColor.systemGray6
        }

        private func setupCards() {
            [trendsCardView, riskCardView].forEach { card in
                card?.backgroundColor = .white
                card?.layer.cornerRadius = 24
                card?.layer.masksToBounds = false
                card?.layer.shadowColor = UIColor.black.cgColor
                card?.layer.shadowOpacity = 0.08
                card?.layer.shadowOffset = CGSize(width: 0, height: 10)
                card?.layer.shadowRadius = 20
            }
        }

        private func setupLabels() {
            [trendsLabel, airlinesLabel].forEach { label in
                label?.numberOfLines = 0
                label?.textColor = .label
                label?.font = UIFont.systemFont(ofSize: 18, weight: .semibold)
                label?.textAlignment = .left
            }
        }

        private func loadDashboard() {
            let flights = StorageManager.shared.loadFlights()

            if flights.isEmpty {
                trendsLabel.text = """
                Delay Trends

                • No saved flight data yet
                • Search and save flights
                """
                airlinesLabel.text = """
                Risk Overview

                • No saved flights available
                """
                return
            }

            let high = flights.filter { $0.riskLevel == .high }.count
            let medium = flights.filter { $0.riskLevel == .medium }.count
            let low = flights.filter { $0.riskLevel == .low }.count
            let avgDelay = flights.map { $0.delayProbability }.reduce(0, +) / flights.count

            trendsLabel.attributedText = makeCardText(
                title: "Delay Trends",
                lines: [
                    "✈️ Saved Flights: \(flights.count)",
                    "⏱ Average Delay: \(avgDelay)%"
                ]
            )

            airlinesLabel.attributedText = makeCardText(
                title: "Risk Overview",
                lines: [
                    "🔴 High Risk: \(high)",
                    "🟠 Medium Risk: \(medium)",
                    "🟢 Low Risk: \(low)"
                ]
            )
        }

        private func makeCardText(title: String, lines: [String]) -> NSAttributedString {
            let result = NSMutableAttributedString()

            let titleAttributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 24, weight: .bold),
                .foregroundColor: UIColor.label
            ]

            let bodyAttributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 18, weight: .semibold),
                .foregroundColor: UIColor.secondaryLabel
            ]

            result.append(NSAttributedString(string: "\(title)\n\n", attributes: titleAttributes))

            for (index, line) in lines.enumerated() {
                result.append(NSAttributedString(string: line, attributes: bodyAttributes))
                if index < lines.count - 1 {
                    result.append(NSAttributedString(string: "\n", attributes: bodyAttributes))
                }
            }

            return result
        }
    }
