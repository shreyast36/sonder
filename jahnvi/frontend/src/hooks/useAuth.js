import { useState, useEffect } from 'react'
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  sendPasswordResetEmail,
  signOut as fbSignOut,
} from 'firebase/auth'
import { auth } from '../lib/firebase'
import { getUserProfile, createUserProfile } from '../lib/api'

export function useAuth() {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          await getUserProfile()
        } catch (err) {
          if (err.status === 404) {
            try {
              await createUserProfile(firebaseUser.displayName || 'Traveller')
            } catch (createErr) {
              console.warn('Profile creation failed (backend may be unavailable):', createErr.message)
            }
          }
        }
        setUser(firebaseUser)
      } else {
        setUser(null)
      }
      setLoading(false)
    })
    return unsubscribe
  }, [])

  async function signIn(email, password) {
    return signInWithEmailAndPassword(auth, email, password)
  }

  async function signUp(email, password, displayName) {
    const cred = await createUserWithEmailAndPassword(auth, email, password)
    if (displayName) {
      await updateProfile(cred.user, { displayName })
    }
    return cred
  }

  async function resetPassword(email) {
    return sendPasswordResetEmail(auth, email)
  }

  async function signOut() {
    await fbSignOut(auth)
    setUser(null)
  }

  return { user, loading, signIn, signUp, resetPassword, signOut }
}
