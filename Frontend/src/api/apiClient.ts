import axios from "axios";

export const apiClient = 
axios.create({
  baseURL: "http://localhost:5000/api/v1", //  cambiar al backend real después
  headers: {
    "Content-Type": "application/json",
  },
})
