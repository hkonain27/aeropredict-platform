# AeroPredict

## Table of Contents

1. Overview
2. Product Spec
3. Wireframes
4. Schema

---

## Overview

### Description

AeroPredict is an iOS mobile app that helps users search for flights and view delay predictions, risk insights, and saved flight tracking. The app provides travelers with useful information before their flight by predicting delays and showing contributing factors.

---

### App Evaluation

**Category:** Travel / Aviation / Productivity

**Mobile:**
This app is designed specifically for mobile users who need quick access to flight predictions on the go. It leverages mobile usability for fast input and real-time interaction.

**Story:**
Travelers often don’t know whether their flight will be delayed until the last minute. AeroPredict helps users plan better by predicting delays ahead of time.

**Market:**
The app targets travelers, students, and frequent flyers. It has a large potential user base, especially among people who travel frequently.

**Habit:**
Users will open the app when planning trips or checking flight updates. It can be used multiple times during a trip.

**Scope:**
The MVP includes flight search, prediction results, saved flights, and dashboard analytics. Additional features can be added later.

---

## Product Spec

### 1. User Stories (Required and Optional)

#### Required Must-have Stories

* User can search for a flight by flight number
* User can view delay prediction and risk level
* User can view contributing factors (weather, traffic, etc.)
* User can save/bookmark flights
* User can view saved flights

#### Optional Nice-to-have Stories

* User can view dashboard analytics (delay trends, airlines)
* User can receive notifications for flight updates
* User can view airline comparisons

---

### 2. Screen Archetypes

**Home Screen**

* User can search for flights
* User can view recent searches

**Prediction Screen**

* User can view delay probability and risk level
* User can view contributing factors
* User can save a flight

**Saved Flights Screen**

* User can view saved flights
* User can tap a flight to view details

**Dashboard Screen**

* User can view delay trends
* User can view top delayed airlines

**Profile Screen**

* User can view user information
* User can manage settings and preferences

---

### 3. Navigation

#### Tab Navigation (Tab to Screen)

* Home
* Saved Flights
* Dashboard
* Profile

#### Flow Navigation (Screen to Screen)

* Home → Prediction Screen

* Prediction Screen → Home

* Saved Flights → Prediction Screen

* Prediction Screen → Saved Flights

---

## Wireframes

### Low-Fidelity Navigation Flow

![Flow](wireframes/wireframes/lowfi-navigation-flowm.jpeg)

### Screens

![Home](wireframes/home-screen.png)
![Prediction](wireframes/prediction-screen.png)
![Saved Flights](wireframes/saved-flights.png)
![Dashboard](wireframes/dashboard-screen.png)
![Profile](wireframes/profile-screen.png)

---

## [BONUS] Digital Wireframes & Mockups

Digital wireframes were created using Figma to represent the app layout and UI structure.

---

## [BONUS] Interactive Prototype

An interactive prototype can be created in Figma to simulate navigation between screens.

---

## Schema

### Models

| Property         | Type   | Description                |
| ---------------- | ------ | -------------------------- |
| flightNumber     | String | Flight identifier          |
| origin           | String | Departure location         |
| destination      | String | Arrival location           |
| delayProbability | Int    | Predicted delay percentage |
| riskLevel        | String | Low / Medium / High        |

---

### Networking

* Fetch flight prediction data
* Retrieve saved flights

#### Example API Request

```swift
// Example placeholder
GET /predict?flightNumber=AA203
```

#### Example Response

```json
{
  "flightNumber": "AA203",
  "delayProbability": 72,
  "riskLevel": "High"
}
```

---
