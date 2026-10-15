/**
 * Shopo Robo - Mobile & Device GPS Live Weather Integration
 * Uses HTML5 Geolocation API and Open-Meteo Free Global Weather API.
 */

const WeatherGPS = {
    currentCity: 'Detecting Location...',
    currentTemp: '--°C',
    weatherDesc: 'Checking GPS...',
    lat: null,
    lon: null,

    init() {
        this.updateBadge();
        this.requestGPSLocation();
    },

    requestGPSLocation() {
        const badgeEl = document.getElementById('weatherGpsBadge');
        if (!navigator.geolocation) {
            this.setFallbackLocation('New Delhi', '28°C Clear');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                this.lat = position.coords.latitude;
                this.lon = position.coords.longitude;
                console.log(`📍 GPS Coordinates received: Lat ${this.lat}, Lon ${this.lon}`);
                await this.fetchRealWeather(this.lat, this.lon);
            },
            (error) => {
                console.warn('GPS location request warning:', error.message);
                // Fallback to IP/Default location
                this.detectCityByIP();
            },
            { timeout: 10000, enableHighAccuracy: true }
        );
    },

    async fetchRealWeather(lat, lon) {
        try {
            // 1. Fetch live temperature from Open-Meteo API
            const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`;
            const weatherRes = await fetch(weatherUrl);
            const weatherData = await weatherRes.json();

            let temp = 28;
            let code = 0;
            if (weatherData && weatherData.current_weather) {
                temp = Math.round(weatherData.current_weather.temperature);
                code = weatherData.current_weather.weathercode;
            }

            const condition = this.getWeatherCondition(code);

            // 2. Reverse geocode coordinates to City Name via free reverse geocoding API
            let city = 'Local Area';
            try {
                const geoUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`;
                const geoRes = await fetch(geoUrl);
                const geoData = await geoRes.json();
                city = geoData.city || geoData.locality || geoData.principalSubdivision || 'Your City';
            } catch (e) {
                city = 'Live GPS';
            }

            this.currentCity = city;
            this.currentTemp = `${temp}°C`;
            this.weatherDesc = condition;
            this.updateBadge();
        } catch (err) {
            console.warn('Weather fetch error:', err);
            this.setFallbackLocation('Live GPS', '29°C Clear');
        }
    },

    async detectCityByIP() {
        try {
            const ipRes = await fetch('https://ipapi.co/json/');
            const ipData = await ipRes.json();
            if (ipData && ipData.latitude && ipData.longitude) {
                await this.fetchRealWeather(ipData.latitude, ipData.longitude);
            } else {
                this.setFallbackLocation('New Delhi', '28°C Clear');
            }
        } catch (e) {
            this.setFallbackLocation('New Delhi', '28°C Clear');
        }
    },

    setFallbackLocation(city, info) {
        this.currentCity = city;
        this.currentTemp = info.split(' ')[0] || '28°C';
        this.weatherDesc = info.split(' ')[1] || 'Clear';
        this.updateBadge();
    },

    getWeatherCondition(code) {
        if (code === 0) return 'Clear';
        if (code >= 1 && code <= 3) return 'Partly Cloudy';
        if (code >= 45 && code <= 48) return 'Hazy';
        if (code >= 51 && code <= 67) return 'Rainy';
        if (code >= 71 && code <= 77) return 'Cold';
        if (code >= 80 && code <= 82) return 'Showers';
        if (code >= 95) return 'Thunderstorm';
        return 'Clear';
    },

    updateBadge() {
        const badgeEl = document.getElementById('weatherGpsBadge');
        if (!badgeEl) return;

        badgeEl.innerHTML = `
            <i class="fa-solid fa-location-crosshairs text-lime-600" title="Click to refresh GPS" style="cursor: pointer;" onclick="WeatherGPS.requestGPSLocation()"></i>
            <span><strong>${this.currentCity}</strong> ${this.currentTemp} ${this.weatherDesc}</span>
        `;
    }
};

window.WeatherGPS = WeatherGPS;
