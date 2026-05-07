import { Routes, Route, Navigate } from 'react-router-dom'
import Welcome         from './pages/Welcome'
import Dashboard       from './pages/Dashboard'
import TripPreferences from './pages/TripPreferences'
import Itinerary       from './pages/Itinerary'
import MatchDetail     from './pages/MatchDetail'
import Chat            from './pages/Chat'
import ApproveDeny     from './pages/ApproveDeny'
import SharedItinerary from './pages/SharedItinerary'
import Notes           from './pages/Notes'

export default function App() {
  return (
    <Routes>
      <Route path="/"                  element={<Welcome/>}/>
      <Route path="/dashboard"         element={<Dashboard/>}/>
      <Route path="/preferences"       element={<TripPreferences/>}/>
      <Route path="/itinerary"         element={<Itinerary/>}/>
      <Route path="/match/:id"         element={<MatchDetail/>}/>
      <Route path="/chat/:sessionId"   element={<Chat/>}/>
      <Route path="/approve/:sessionId"element={<ApproveDeny/>}/>
      <Route path="/shared/:id"        element={<SharedItinerary/>}/>
      <Route path="/notes/:id"         element={<Notes/>}/>
      <Route path="*"                  element={<Navigate to="/" replace/>}/>
    </Routes>
  )
}
