/**
 * Weather Actions - Using Google Places + OpenWeatherMap fallback
 * Since user has Google Places API enabled, we can use that for geocoding
 */

import { ActionResult } from './index';

// Use wttr.in as a free, no-API-key weather service
export async function handleGetWeather(params: {
    location: string;
}): Promise<ActionResult> {
    try {
        const location = encodeURIComponent(params.location);

        // Use wttr.in - free weather API, no key needed
        const response = await fetch(`https://wttr.in/${location}?format=j1`);

        if (!response.ok) {
            throw new Error('Weather service unavailable');
        }

        const data = await response.json();

        const current = data.current_condition?.[0];
        const area = data.nearest_area?.[0];

        if (!current) {
            throw new Error('Could not get weather data');
        }

        const locationName = area?.areaName?.[0]?.value || params.location;
        const country = area?.country?.[0]?.value || '';
        const temp = current.temp_F || current.temp_C;
        const tempUnit = current.temp_F ? 'F' : 'C';
        const feelsLike = current.FeelsLikeF || current.FeelsLikeC;
        const condition = current.weatherDesc?.[0]?.value || 'Unknown';
        const humidity = current.humidity;
        const windSpeed = current.windspeedMiles || current.windspeedKmph;
        const windUnit = current.windspeedMiles ? 'mph' : 'km/h';

        const message = `In ${locationName}${country ? ', ' + country : ''}, it's currently ${temp}°${tempUnit} ` +
            `and ${condition.toLowerCase()}. Feels like ${feelsLike}°${tempUnit}. ` +
            `Humidity is ${humidity}% with winds at ${windSpeed} ${windUnit}. `;

        return {
            success: true,
            message,
            data: {
                location: locationName,
                temperature: temp,
                feelsLike,
                condition,
                humidity,
                windSpeed,
            },
        };
    } catch (error) {
        return {
            success: false,
            message: `Couldn't get weather for ${params.location}. Please try again.`,
        };
    }
}
