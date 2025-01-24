import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image, ActivityIndicator, Dimensions } from 'react-native';
import { Camera } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

const API_URL = 'http://192.168.11.106:8000/process/'; 

export default function App() {
  const [hasPermission, setHasPermission] = useState(null);
  const [type, setType] = useState(Camera.Constants.Type.back);
  const [capturedImage, setCapturedImage] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const cameraRef = useRef(null);
  
  const windowHeight = Dimensions.get('window').height;
  const windowWidth = Dimensions.get('window').width;

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const takePicture = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync();
        setCapturedImage(photo.uri);
        await processImage(photo.uri);
      } catch (error) {
        console.error('Erreur lors de la capture:', error);
      }
    }
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 1,
    });

    if (!result.canceled) {
      setCapturedImage(result.assets[0].uri);
      await processImage(result.assets[0].uri);
    }
  };

  const processImage = async (uri) => {
    setProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', {
        uri,
        type: 'image/jpeg',
        name: 'photo.jpg',
      });

      const response = await axios.post(API_URL, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.valid) {
        setResult({
          valid: true,
          cin: response.data.cin,
          name: response.data.name,        // Vérification de la structure des données ici
          surname: response.data.first_name, // Vérification ici aussi
          birthDate: response.data.birth_date,
          message: 'CIN Validé avec succès!',
        });
      } else {
        setResult({
          valid: false,
          message: response.data.message || 'CIN Invalide',
        });
      }
    } catch (error) {
      console.error('Erreur lors du traitement:', error);
      setResult({ error: 'Erreur lors du traitement de l\'image' });
    } finally {
      setProcessing(false);
    }
  };

  const resetCapture = () => {
    setCapturedImage(null);
    setResult(null);
  };

  if (hasPermission === null) {
    return <View><Text>Demande d'accès à la caméra...</Text></View>;
  }
  if (hasPermission === false) {
    return <Text>Pas d'accès à la caméra</Text>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>Analyse de Carte d'Identité</Text>
      </View>

      {!capturedImage ? (
        <Camera style={[styles.camera, { height: windowHeight - 100 }]} type={type} ref={cameraRef}>
          <View style={styles.overlay}>
            <View style={styles.frame} />
          </View>
          <View style={styles.buttonContainer}>
            <TouchableOpacity style={styles.button} onPress={takePicture}>
              <Text style={styles.text}>Prendre Photo</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.button} onPress={pickImage}>
              <Text style={styles.text}>Choisir Image</Text>
            </TouchableOpacity>
          </View>
        </Camera>
      ) : (
        <View style={styles.previewContainer}>
          <Image source={{ uri: capturedImage }} style={styles.preview} />
          {processing ? (
            <ActivityIndicator size="large" color="#4CAF50" />
          ) : (
            <>
              {result && (
                <View style={styles.resultContainer}>
                  <Text style={styles.resultText}>
                    {result.valid ? 'CIN Valide !' : result.message || 'CIN Invalide'}
                  </Text>
                  {result.cin && <Text style={styles.resultText}>CIN: {result.cin}</Text>}
                  {result.name && <Text style={styles.resultText}>Nom: {result.name}</Text>}
                  {result.surname && <Text style={styles.resultText}>Prénom: {result.surname}</Text>}
                  {result.birthDate && <Text style={styles.resultText}>Date de naissance: {result.birthDate}</Text>}
                </View>
              )}
              <TouchableOpacity style={styles.button} onPress={resetCapture}>
                <Text style={styles.text}>Nouvelle Photo</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f7f7',
  },
  header: {
    width: '100%',
    padding: 20,
    backgroundColor: '#4CAF50',
    alignItems: 'center',
    position: 'absolute',
    top: 0,
    zIndex: 1,
  },
  headerText: {
    fontSize: 20,
    color: 'white',
    fontWeight: 'bold',
  },
  camera: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  frame: {
    width: 300,
    height: 200,
    borderWidth: 2,
    borderColor: '#fff',
    borderRadius: 10,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    position: 'absolute',
    bottom: 20,
    width: '100%',
  },
  button: {
    backgroundColor: '#4CAF50', 
    padding: 15,
    borderRadius: 25,
    margin: 10,
  },
  text: {
    fontSize: 18,
    color: 'white',
    fontWeight: 'bold',
  },
  previewContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  preview: {
    width: '100%',
    height: '70%',
  },
  resultContainer: {
    padding: 20,
    margin: 20,
    backgroundColor: '#e3f2fd', 
    borderRadius: 15,
    alignItems: 'center',
  },
  resultText: {
    fontSize: 16,
    color: '#333',
    marginBottom: 5,
  },
});
