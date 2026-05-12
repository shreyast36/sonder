import { useState, useEffect } from 'react'
import { doc, collection, onSnapshot, query } from 'firebase/firestore'
import { db } from '../lib/firebase'
import { useToast } from '../components/Toast'
import { addSharedActivity, addSharedNote } from '../lib/api'

export function useDocument(collectionName, id) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!id) return
    const ref = doc(db, collectionName, id)
    const unsub = onSnapshot(
      ref,
      (snap) => {
        setData(snap.exists() ? { id: snap.id, ...snap.data() } : null)
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      },
    )
    return unsub
  }, [collectionName, id])

  return { data, loading, error }
}

export function useCollection(collectionName, constraints = []) {
  const [data, setData]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    const ref = collection(db, collectionName)
    const q   = constraints.length ? query(ref, ...constraints) : ref
    const unsub = onSnapshot(
      q,
      (snap) => {
        setData(snap.docs.map(d => ({ id: d.id, ...d.data() })))
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      },
    )
    return unsub
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collectionName])

  return { data, loading, error }
}

export function useSharedItinerary(itineraryId) {
  const { data: itinerary, loading } = useDocument('shared_itineraries', itineraryId)
  const toast = useToast()

  async function handleConflict(fn) {
    try {
      await fn()
    } catch (err) {
      if (err.status === 409) {
        toast({ title: 'Your co-traveller just made a change — review and try again' })
      } else {
        throw err
      }
    }
  }

  function addActivity(activity, dayNumber) {
    return handleConflict(() =>
      addSharedActivity(itineraryId, activity, dayNumber, itinerary?.version),
    )
  }

  function addNote(note) {
    return handleConflict(() =>
      addSharedNote(itineraryId, note, itinerary?.version),
    )
  }

  return { itinerary, version: itinerary?.version, loading, addActivity, addNote }
}
