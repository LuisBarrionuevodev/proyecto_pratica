import axios from "axios";

export const apiClient = 
axios.create({
  baseURL: "http://localhost:5000/", //  cambiar al backend real después
  headers: {
    "Content-Type": "application/json",
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
