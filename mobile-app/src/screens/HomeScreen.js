import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import RainCheckService from '../services/RainCheckService';

const HomeScreen = () => {
  const [lastCheck, setLastCheck] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [weatherData, setWeatherData] = useState(null);

  useEffect(() => {
    loadLastCheck();
  }, []);

  const loadLastCheck = async () => {
    try {
      const lastCheckData = await AsyncStorage.getItem('lastRainCheck');
      if (lastCheckData) {
        setLastCheck(JSON.parse(lastCheckData));
      }
    } catch (error) {
      console.error('Error loading last check:', error);
    }
  };

  const checkRainNow = async () => {
    setIsRefreshing(true);
    try {
      await RainCheckService.checkRainConditions();
      
      // Update last check time
      const now = new Date();
      const checkData = {
        timestamp: now.toISOString(),
        status: 'completed'
      };
      
      await AsyncStorage.setItem('lastRainCheck', JSON.stringify(checkData));
      setLastCheck(checkData);
      
      Alert.alert('Success', 'Rain check completed! Check your notifications.');
    } catch (error) {
      console.error('Error checking rain:', error);
      Alert.alert('Error', 'Failed to check rain conditions');
    } finally {
      setIsRefreshing(false);
    }
  };

  const formatLastCheck = () => {
    if (!lastCheck) return 'Never';
    
    const date = new Date(lastCheck.timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)} hours ago`;
    return date.toLocaleDateString();
  };

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={isRefreshing} onRefresh={checkRainNow} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>MotoRain</Text>
        <Text style={styles.subtitle}>Your Personal Rain Alert System</Text>
      </View>

      <View style={styles.statusCard}>
        <Text style={styles.statusTitle}>Last Check</Text>
        <Text style={styles.statusValue}>{formatLastCheck()}</Text>
      </View>

      <View style={styles.quickActions}>
        <TouchableOpacity style={styles.actionButton} onPress={checkRainNow}>
          <Text style={styles.actionButtonText}>🌤️ Check Rain Now</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>How it works</Text>
        <Text style={styles.infoText}>
          • Set your commute schedule in the Commute tab{'\n'}
          • We'll check weather 30 minutes before your commute{'\n'}
          • Get notifications: ✅ Clear weather or 🌧️ Rain alert{'\n'}
          • Never get caught in the rain again!
        </Text>
      </View>

      <View style={styles.tipsCard}>
        <Text style={styles.tipsTitle}>💡 Tips</Text>
        <Text style={styles.tipsText}>
          • Make sure to set your home and work addresses{'\n'}
          • Enable notifications for the best experience{'\n'}
          • Check the Weather tab for detailed forecasts{'\n'}
          • Adjust commute times as needed
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
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
  },
  statusCard: {
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
  statusTitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 5,
  },
  statusValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  quickActions: {
    margin: 15,
  },
  actionButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  actionButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
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
  tipsCard: {
    backgroundColor: '#FFF3E0',
    margin: 15,
    padding: 20,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#FF9800',
  },
  tipsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#E65100',
    marginBottom: 10,
  },
  tipsText: {
    fontSize: 14,
    color: '#BF360C',
    lineHeight: 20,
  },
});

export default HomeScreen;
