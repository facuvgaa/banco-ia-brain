import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL
})

export const chatService = {
    sendMessage(text){
        return api.post('/chat', {prompt: text})
    }
}