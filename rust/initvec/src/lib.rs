use std::mem::{self, MaybeUninit};

use fixedbitset::FixedBitSet;

#[derive(Debug)]
pub struct InitVec<T> {
    slots: Vec<MaybeUninit<T>>,
    init: FixedBitSet,
    init_count: usize,
}

impl<T> InitVec<T> {
    /// Create new vector of `capacity` initially uninitialized slots for items `T`.
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            slots: std::iter::repeat_with(MaybeUninit::uninit)
                .take(capacity)
                .collect(),
            init: FixedBitSet::with_capacity(capacity),
            init_count: 0,
        }
    }

    /// Initialize slot i` with `item`.
    ///
    /// Note that this drops any value previously inserted at position `i`.
    ///
    /// ### Panics
    /// This function panics if `i` is out of bounds (see [`InitVec::with_capacity`]).
    pub fn insert(&mut self, i: usize, item: T) {
        let slot = &mut self.slots[i];

        // SAFETY: slots and init have the same length and i was just checked to be in bounds
        if unsafe { self.init.put_unchecked(i) } {
            // replace an already initialized item in this slot
            let _ = mem::replace(unsafe { slot.assume_init_mut() }, item);
        } else {
            // initialize slot
            slot.write(item);
            self.init_count += 1;
        }
    }

    #[inline]
    fn into_parts(mut self) -> (Vec<MaybeUninit<T>>, FixedBitSet, usize) {
        (
            mem::take(&mut self.slots),
            mem::take(&mut self.init),
            mem::take(&mut self.init_count),
        )
    }

    /// Turn `self` into a vector of initialized items.
    ///
    /// ### Returns
    ///  - `Ok(items)` when all items were initialized
    ///  - `Err(items)` when some items were uninitialized. Then the portion of successfully
    ///    initialized items is returned in the error.
    pub fn try_init(self) -> Result<Vec<T>, Vec<T>> {
        if self.init_count < self.slots.len() {
            Err(self.init_some())
        } else {
            // SAFETY: all items were successfully written as witnessed by the init_count
            Ok(unsafe { self.init_all() })
        }
    }

    /// Turn `self` into a vector of initialized items.
    ///
    /// Returns `None` when some items were uninitialized.
    pub fn init(self) -> Option<Vec<T>> {
        if self.init_count < self.slots.len() {
            None
        } else {
            // SAFETY: all items were successfully written as witnessed by the init_count
            Some(unsafe { self.init_all() })
        }
    }

    /// Safety: caller must ensure that all slots are initialized
    unsafe fn init_all(self) -> Vec<T> {
        let (items, ..) = self.into_parts();
        // SAFETY: by the contract of this method
        unsafe { mem::transmute::<Vec<MaybeUninit<T>>, Vec<T>>(items) }
    }

    fn init_some(self) -> Vec<T> {
        let (mut slots, init, init_count) = self.into_parts();

        let mut vec = Vec::with_capacity(init_count);

        for i in init.into_ones() {
            // SAFETY: slots and init have the same length
            let slot = unsafe { slots.get_unchecked_mut(i) };
            let slot = mem::replace(slot, MaybeUninit::uninit());
            // SAFETY: slots[i] is initialized iff init[i] is set
            vec.push(unsafe { slot.assume_init() });
        }

        vec
    }
}

impl<T> Drop for InitVec<T> {
    fn drop(&mut self) {
        for i in self.init.ones() {
            // SAFETY: slots and init have the same length
            let slot = unsafe { self.slots.get_unchecked_mut(i) };
            // SAFETY: slots[i] is initialized iff init[i] is true
            unsafe { slot.assume_init_drop() };
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_init() {
        let mut vec = InitVec::with_capacity(3);
        vec.insert(1, "y");
        vec.insert(2, "z");
        vec.insert(0, "x");
        assert_eq!(Some(vec!["x", "y", "z"]), vec.init());
    }

    #[test]
    fn some_uninit() {
        let mut vec = InitVec::with_capacity(3);
        vec.insert(2, "z");
        vec.insert(0, "x");
        assert!(vec.init().is_none());
    }

    #[test]
    fn try_all_init() {
        let mut vec = InitVec::with_capacity(3);
        vec.insert(1, "y");
        vec.insert(2, "z");
        vec.insert(0, "x");
        assert_eq!(Ok(vec!["x", "y", "z"]), vec.try_init());
    }

    #[test]
    fn try_some_uninit() {
        let mut vec = InitVec::with_capacity(3);
        vec.insert(2, "z");
        vec.insert(0, "x");
        assert_eq!(Err(vec!["x", "z"]), vec.try_init());
    }

    #[test]
    #[should_panic(expected = "index out of bounds")]
    fn insert_out_of_bounds() {
        let mut vec = InitVec::with_capacity(3);
        vec.insert(10, "fail");
    }

    #[test]
    fn init_with_refs() {
        let data = [4, 2];

        let mut vec = InitVec::with_capacity(data.len());

        data.iter().enumerate().for_each(|(i, item_ref)| {
            vec.insert(i, item_ref);
        });

        assert_eq!(Some(vec![&4, &2]), vec.init());
    }
}
