import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Image,
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const WeatherScreen = () => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [homeAddress, setHomeAddress] = useState('');
  const [workAddress, setWorkAddress] = useState('');

  useEffect(() => {
    loadAddresses();
  }, []);

  const loadAddresses = async () => {
    try {
      const settings = await AsyncStorage.getItem('commuteSettings');
      if (settings) {
        const { homeAddress: home, workAddress: work } = JSON.parse(settings);
        setHomeAddress(home);
        setWorkAddress(work);
      }
    } catch (error) {
      console.error('Error loading addresses:', error);
    }
  };

  const checkWeather = async () => {
    if (!homeAddress || !workAddress) {
      Alert.alert('Missing Information', 'Please set your home and work addresses in the Commute settings first.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://your-backend-url:8000/check_rain/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user: 'mobile_user',
          home: homeAddress,
          work: workAddress,
          vehicle: 'bike'
        })
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();
      setWeatherData(data);
      
      // Save the weather data
      await AsyncStorage.setItem('lastWeatherData', JSON.stringify(data));
      
    } catch (error) {
      console.error('Error checking weather:', error);
      Alert.alert('Error', 'Failed to check weather conditions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadLastWeatherData = async () => {
    try {
      const lastData = await AsyncStorage.getItem('lastWeatherData');
      if (lastData) {
        setWeatherData(JSON.parse(lastData));
      }
    } catch (error) {
      console.error('Error loading last weather data:', error);
    }
  };

  useEffect(() => {
    loadLastWeatherData();
  }, []);

  const getWeatherIcon = (willRain) => {
    return willRain ? '🌧️' : '☀️';
  };

  const getWeatherColor = (willRain) => {
    return willRain ? '#FF5722' : '#4CAF50';
  };

  const getWeatherMessage = (willRain, condition) => {
    if (willRain) {
      return `⚠️ ${condition || 'Rain expected on your route'}`;
    } else {
      return `✅ ${condition || 'Clear weather - no rain expected'}`;
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Weather Forecast</Text>
        <Text style={styles.subtitle}>Current conditions for your commute</Text>
      </View>

      {!homeAddress || !workAddress ? (
        <View style={styles.warningCard}>
          <Text style={styles.warningTitle}>⚠️ Setup Required</Text>
          <Text style={styles.warningText}>
            Please set your home and work addresses in the Commute settings to check weather conditions.
          </Text>
        </View>
      ) : (
        <>
          <View style={styles.routeCard}>
            <Text style={styles.routeTitle}>Your Route</Text>
            <Text style={styles.routeText}>From: {homeAddress}</Text>
            <Text style={styles.routeText}>To: {workAddress}</Text>
          </View>

          <TouchableOpacity 
            style={[styles.checkButton, loading && styles.disabledButton]} 
            onPress={checkWeather}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.checkButtonText}>🌤️ Check Weather Now</Text>
            )}
          </TouchableOpacity>

          {weatherData && (
            <View style={styles.weatherCard}>
              <View style={styles.weatherHeader}>
                <Text style={styles.weatherIcon}>
                  {getWeatherIcon(weatherData.will_rain)}
                </Text>
                <View style={styles.weatherInfo}>
                  <Text style={[
                    styles.weatherStatus,
                    { color: getWeatherColor(weatherData.will_rain) }
                  ]}>
                    {getWeatherMessage(weatherData.will_rain, weatherData.weather_condition)}
                  </Text>
                  <Text style={styles.weatherTime}>
                    Last updated: {new Date().toLocaleTimeString()}
                  </Text>
                </View>
              </View>

              {weatherData.image_b64 && (
                <View style={styles.imageContainer}>
                  <Image
                    source={{ uri: `data:image/png;base64,${weatherData.image_b64}` }}
                    style={styles.routeImage}
                    resizeMode="contain"
                  />
                </View>
              )}

              <View style={styles.detailsCard}>
                <Text style={styles.detailsTitle}>Details</Text>
                <Text style={styles.detailsText}>
                  Vehicle: {weatherData.vehicle || 'Bike'}
                </Text>
                <Text style={styles.detailsText}>
                  Status: {weatherData.status || 'OK'}
                </Text>
                {weatherData.weather_condition && (
                  <Text style={styles.detailsText}>
                    Condition: {weatherData.weather_condition}
                  </Text>
                )}
              </View>
            </View>
          )}
        </>
      )}

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>About Weather Checks</Text>
        <Text style={styles.infoText}>
          • Weather data is fetched from radar imagery{'\n'}
          • Checks are performed 30 minutes before your commute{'\n'}
          • Notifications are sent automatically{'\n'}
          • Manual checks are always available here
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#2196F3',
    padding: 20,
    paddingTop: 40,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
  },
  warningCard: {
    backgroundColor: '#FFF3E0',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#FF9800',
  },
  warningTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#E65100',
    marginBottom: 10,
  },
  warningText: {
    fontSize: 14,
    color: '#BF360C',
    lineHeight: 20,
  },
  routeCard: {
    backgroundColor: 'white',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  routeTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  routeText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  checkButton: {
    backgroundColor: '#4CAF50',
    margin: 15,
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  checkButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  weatherCard: {
    backgroundColor: 'white',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  weatherHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  weatherIcon: {
    fontSize: 40,
    marginRight: 15,
  },
  weatherInfo: {
    flex: 1,
  },
  weatherStatus: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  weatherTime: {
    fontSize: 12,
    color: '#666',
  },
  imageContainer: {
    alignItems: 'center',
    marginVertical: 15,
  },
  routeImage: {
    width: '100%',
    height: 200,
    borderRadius: 10,
  },
  detailsCard: {
    backgroundColor: '#f8f9fa',
    padding: 15,
    borderRadius: 8,
    marginTop: 10,
  },
  detailsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  detailsText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  infoCard: {
    backgroundColor: 'white',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});

export default WeatherScreen;
