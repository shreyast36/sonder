import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import Welcome         from './pages/Welcome'
import SignUp          from './pages/SignUp'
import AuthAction      from './pages/AuthAction'
import Dashboard       from './pages/Dashboard'
import TripPreferences from './pages/TripPreferences'
import PersonaReveal   from './pages/PersonaReveal'
import Itinerary       from './pages/Itinerary'
import Companions      from './pages/Companions'
import Journal         from './pages/Journal'
import Destination     from './pages/Destination'
import MatchDetail     from './pages/MatchDetail'
import Chat            from './pages/Chat'
import ChatAsFake      from './pages/ChatAsFake'
import ApproveDeny     from './pages/ApproveDeny'
import SharedItinerary from './pages/SharedItinerary'
import Notes           from './pages/Notes'
import Discover               from './pages/Discover'
import TravellerCompatibility from './pages/TravellerCompatibility'
import LuxCursor              from './components/LuxCursor'
import { ToastProvider } from './components/Toast'

function Page({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  const location = useLocation()

  return (
    <ToastProvider>
      <ScrollToTop/>
      <LuxCursor/>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/"                   element={<Page><Welcome/></Page>}/>
          <Route path="/signup"             element={<Page><SignUp/></Page>}/>
          <Route path="/signin"             element={<Page><SignUp/></Page>}/>
          <Route path="/auth/action"        element={<Page><AuthAction/></Page>}/>
          <Route path="/dashboard"          element={<Page><Dashboard/></Page>}/>
          <Route path="/preferences"        element={<Page><TripPreferences/></Page>}/>
          <Route path="/persona-reveal"     element={<Page><PersonaReveal/></Page>}/>
          <Route path="/itinerary"          element={<Page><Itinerary/></Page>}/>
          <Route path="/companions/:itineraryId" element={<Page><Companions/></Page>}/>
          <Route path="/journal/:itineraryId"    element={<Page><Journal/></Page>}/>
          <Route path="/destination/:city"       element={<Page><Destination/></Page>}/>
          <Route path="/match/:id"          element={<Page><MatchDetail/></Page>}/>
          <Route path="/chat/:sessionId"    element={<Page><Chat/></Page>}/>
          <Route path="/chat-as/:sessionId/:profileId" element={<Page><ChatAsFake/></Page>}/>
          <Route path="/approve/:sessionId" element={<Page><ApproveDeny/></Page>}/>
          <Route path="/shared/:id"         element={<Page><SharedItinerary/></Page>}/>
          <Route path="/notes/:id"          element={<Page><Notes/></Page>}/>
          <Route path="/discover"           element={<Page><Discover/></Page>}/>
          <Route path="/compatibility"      element={<Page><TravellerCompatibility/></Page>}/>
          <Route path="*"                   element={<Navigate to="/" replace/>}/>
        </Routes>
      </AnimatePresence>
    </ToastProvider>
  )
}
