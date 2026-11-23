import assert from 'node:assert/strict';
import {
  METRIC_CONFIGS,
  getAirQualityColor,
  getAirQualityCategory,
  getTemperatureColor,
  getGreeneryColor,
  getTrafficColor,
  buildRouteSegments,
} from './environmentalSegmentation.js';

// 1. Metric configs integrity
assert.ok(METRIC_CONFIGS.air_quality.legend.length >= 5);
assert.ok(METRIC_CONFIGS.temperature.legend.length >= 5);

// 2. Air quality colors & categories
assert.equal(getAirQualityColor(15), '#10b981'); // Good
assert.equal(getAirQualityCategory(15), 'Good');
assert.equal(getAirQualityColor(35), '#3b82f6'); // Fair
assert.equal(getAirQualityCategory(35), 'Fair');
assert.equal(getAirQualityColor(55), '#f59e0b'); // Moderate
assert.equal(getAirQualityCategory(55), 'Moderate');
assert.equal(getAirQualityColor(75), '#ef4444'); // Poor
assert.equal(getAirQualityCategory(75), 'Poor');
assert.equal(getAirQualityColor(null), '#94a3b8'); // Missing
assert.equal(getAirQualityCategory(null), 'Unknown');

// 3. Temperature colors
assert.equal(getTemperatureColor(2), '#3b82f6'); // < 5 Cold
assert.equal(getTemperatureColor(10), '#06b6d4'); // 5-14 Cool
assert.equal(getTemperatureColor(18), '#10b981'); // 15-22 Mild
assert.equal(getTemperatureColor(25), '#f59e0b'); // 23-28 Warm
assert.equal(getTemperatureColor(32), '#ef4444'); // > 28 Hot
assert.equal(getTemperatureColor(null), '#94a3b8'); // Missing

// 4. Greenery & Traffic colors
assert.equal(getGreeneryColor(80), '#15803d');
assert.equal(getGreeneryColor(10), '#cbd5e1');
assert.equal(getGreeneryColor(null), '#94a3b8');

assert.equal(getTrafficColor(15), '#10b981');
assert.equal(getTrafficColor(70), '#ef4444');
assert.equal(getTrafficColor(null), '#94a3b8');

// 5. Short / Invalid routes
assert.deepEqual(buildRouteSegments(null), []);
assert.deepEqual(buildRouteSegments({ coordinates: [] }), []);
assert.deepEqual(buildRouteSegments({ coordinates: [[51.5, -0.1]] }), []);

// 6. Default metric returns single unbroken route
const mockCoords = [
  [51.500, -0.100],
  [51.502, -0.095],
  [51.504, -0.090],
  [51.506, -0.085],
  [51.508, -0.080],
  [51.510, -0.075],
];

const mockRoute = {
  id: 'route_0',
  name: 'Route 1',
  color: '#2563eb',
  coordinates: mockCoords,
  environment: {
    sample_points: [
      {
        point_index: 0,
        lat: 51.500,
        lon: -0.100,
        air_quality: { european_aqi: { value: 15, category: 'Good' } },
        weather: { temperature_c: 18.5 },
      },
      {
        point_index: 2,
        lat: 51.504,
        lon: -0.090,
        air_quality: { european_aqi: { value: 35, category: 'Fair' } },
        weather: { temperature_c: 19.0 },
      },
      {
        point_index: 5,
        lat: 51.510,
        lon: -0.075,
        air_quality: { european_aqi: { value: 65, category: 'Poor' } },
        weather: { temperature_c: 20.2 },
      },
    ],
  },
};

const defaultSegs = buildRouteSegments(mockRoute, 'default');
assert.equal(defaultSegs.length, 1);
assert.equal(defaultSegs[0].color, '#2563eb');
assert.equal(defaultSegs[0].coordinates.length, mockCoords.length);

// 7. Multi-segment construction for Air Quality
const aqiSegs = buildRouteSegments(mockRoute, 'air_quality');
assert.equal(aqiSegs.length, 3);
assert.equal(aqiSegs[0].color, '#10b981'); // 15 EAQI (Good)
assert.equal(aqiSegs[1].color, '#3b82f6'); // 35 EAQI (Fair)
assert.equal(aqiSegs[2].color, '#ef4444'); // 65 EAQI (Poor)
assert.equal(aqiSegs[0].metricValue, 15);
assert.equal(aqiSegs[1].metricValue, 35);
assert.equal(aqiSegs[2].metricValue, 65);

// 8. Zero gaps between consecutive segments
for (let i = 0; i < aqiSegs.length - 1; i++) {
  const currentEnd = aqiSegs[i].coordinates[aqiSegs[i].coordinates.length - 1];
  const nextStart = aqiSegs[i + 1].coordinates[0];
  assert.deepEqual(currentEnd, nextStart, `Gap detected between segment ${i} and ${i + 1}`);
}

// 9. Multi-segment construction for Temperature
const tempSegs = buildRouteSegments(mockRoute, 'temperature');
assert.equal(tempSegs.length, 3);
assert.equal(tempSegs[0].metricValue, 18.5);
assert.equal(tempSegs[0].color, '#10b981'); // Mild

// 10. Missing environmental data handling (Never replaces null with zero)
const routeWithMissingData = {
  id: 'route_missing',
  coordinates: mockCoords,
  environment: {
    sample_points: [
      {
        point_index: 0,
        lat: 51.500,
        lon: -0.100,
        air_quality: { european_aqi: { value: null } },
        weather: { temperature_c: null },
      },
      {
        point_index: 5,
        lat: 51.510,
        lon: -0.075,
        air_quality: { european_aqi: { value: 18 } },
        weather: { temperature_c: 16.0 },
      },
    ],
  },
};

const missingAqiSegs = buildRouteSegments(routeWithMissingData, 'air_quality');
assert.equal(missingAqiSegs.length, 2);
assert.equal(missingAqiSegs[0].isMissing, true);
assert.equal(missingAqiSegs[0].color, '#94a3b8');
assert.equal(missingAqiSegs[0].metricValue, null);
assert.notEqual(missingAqiSegs[0].metricValue, 0);

assert.equal(missingAqiSegs[1].isMissing, false);
assert.equal(missingAqiSegs[1].color, '#10b981');
assert.equal(missingAqiSegs[1].metricValue, 18);

console.log('All environmental segmentation tests passed successfully!');
