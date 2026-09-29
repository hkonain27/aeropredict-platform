# AeroPredict interface

From this directory run `npm ci`, then `npm run dev`. Start the Python server from the repository root using `python -m backend.app`. The default API is `http://localhost:5001`; set `VITE_API_BASE_URL` before building to change it.

The interface searches US domestic routes and displays model-estimated arrival delay minutes. A trained model and configured SerpApi/WeatherAPI request budgets are required. The server token, when used, is entered in **Server access** and kept only in component memory. Provider keys belong exclusively in the Python process environment.

Run `npm run build` for a production bundle and `npm run lint` for static checks. See the root [setup guide](../README.md) for training and deployment.
