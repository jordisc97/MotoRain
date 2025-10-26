import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Switch,
  TextInput,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';

const SettingsScreen = () => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [homeAddress, setHomeAddress] = useState('');
  const [workAddress, setWorkAddress] = useState('');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [isEditingAddresses, setIsEditingAddresses] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await AsyncStorage.getItem('commuteSettings');
      if (settings) {
        const parsedSettings = JSON.parse(settings);
        setNotificationsEnabled(parsedSettings.notificationsEnabled !== false);
        setHomeAddress(parsedSettings.homeAddress || '');
        setWorkAddress(parsedSettings.workAddress || '');
      }

      const savedApiUrl = await AsyncStorage.getItem('apiUrl');
      if (savedApiUrl) {
        setApiUrl(savedApiUrl);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      const settings = {
        notificationsEnabled,
        homeAddress,
        workAddress,
      };
      await AsyncStorage.setItem('commuteSettings', JSON.stringify(settings));
      await AsyncStorage.setItem('apiUrl', apiUrl);
      
      Alert.alert('Success', 'Settings saved successfully!');
      setIsEditingAddresses(false);
    } catch (error) {
      console.error('Error saving settings:', error);
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const testNotification = () => {
    PushNotification.localNotification({
      title: 'MotoRain Test',
      message: 'This is a test notification!',
      playSound: true,
      soundName: 'default',
    });
  };

  const clearAllData = () => {
    Alert.alert(
      'Clear All Data',
      'This will clear all your settings and data. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.clear();
              Alert.alert('Success', 'All data cleared successfully!');
              // Reload settings
              loadSettings();
            } catch (error) {
              console.error('Error clearing data:', error);
              Alert.alert('Error', 'Failed to clear data');
            }
          },
        },
      ]
    );
  };

  const exportSettings = async () => {
    try {
      const settings = await AsyncStorage.getItem('commuteSettings');
      const apiUrl = await AsyncStorage.getItem('apiUrl');
      
      const exportData = {
        commuteSettings: settings ? JSON.parse(settings) : null,
        apiUrl: apiUrl || 'http://localhost:8000',
        exportDate: new Date().toISOString(),
      };

      // In a real app, you would save this to a file or share it
      Alert.alert('Export Data', JSON.stringify(exportData, null, 2));
    } catch (error) {
      console.error('Error exporting settings:', error);
      Alert.alert('Error', 'Failed to export settings');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Settings</Text>
        <Text style={styles.subtitle}>Configure your MotoRain experience</Text>
      </View>

      {/* Notifications Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Enable Rain Alerts</Text>
          <Switch
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={notificationsEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>
        <TouchableOpacity style={styles.testButton} onPress={testNotification}>
          <Text style={styles.buttonText}>Test Notification</Text>
        </TouchableOpacity>
      </View>

      {/* Addresses Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Addresses</Text>
          <TouchableOpacity onPress={() => setIsEditingAddresses(!isEditingAddresses)}>
            <Text style={styles.editButton}>
              {isEditingAddresses ? 'Done' : 'Edit'}
            </Text>
          </TouchableOpacity>
        </View>
        
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Home Address</Text>
          <TextInput
            style={styles.textInput}
            value={homeAddress}
            onChangeText={setHomeAddress}
            placeholder="Enter your home address"
            editable={isEditingAddresses}
          />
        </View>
        
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Work Address</Text>
          <TextInput
            style={styles.textInput}
            value={workAddress}
            onChangeText={setWorkAddress}
            placeholder="Enter your work address"
            editable={isEditingAddresses}
          />
        </View>
      </View>

      {/* API Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>API Configuration</Text>
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Backend URL</Text>
          <TextInput
            style={styles.textInput}
            value={apiUrl}
            onChangeText={setApiUrl}
            placeholder="http://localhost:8000"
            keyboardType="url"
          />
        </View>
      </View>

      {/* App Information */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>App Information</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Version</Text>
          <Text style={styles.infoValue}>1.0.0</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Build</Text>
          <Text style={styles.infoValue}>2024.1</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Last Updated</Text>
          <Text style={styles.infoValue}>{new Date().toLocaleDateString()}</Text>
        </View>
      </View>

      {/* Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Actions</Text>
        <TouchableOpacity style={styles.actionButton} onPress={saveSettings}>
          <Text style={styles.buttonText}>Save Settings</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.exportButton} onPress={exportSettings}>
          <Text style={styles.buttonText}>Export Settings</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.clearButton} onPress={clearAllData}>
          <Text style={styles.buttonText}>Clear All Data</Text>
        </TouchableOpacity>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          MotoRain - Never get caught in the rain again! 🌧️
        </Text>
        <Text style={styles.footerSubtext}>
          Made with ❤️ for commuters
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
  section: {
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
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  editButton: {
    color: '#2196F3',
    fontSize: 16,
    fontWeight: 'bold',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  settingLabel: {
    fontSize: 16,
    color: '#333',
  },
  inputGroup: {
    marginBottom: 15,
  },
  inputLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#f9f9f9',
  },
  testButton: {
    backgroundColor: '#2196F3',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  actionButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  exportButton: {
    backgroundColor: '#FF9800',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  clearButton: {
    backgroundColor: '#F44336',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
  },
  infoValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: 'bold',
  },
  footer: {
    alignItems: 'center',
    padding: 20,
    marginBottom: 40,
  },
  footerText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 5,
  },
  footerSubtext: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
});

export default SettingsScreen;
