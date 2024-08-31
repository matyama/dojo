/// Writes a formatted expression into given buffer.
///
/// If successful, returns the number of bytes written.
#[macro_export]
macro_rules! write_fmt {
    ($buf:ident, $fmt:literal) => {{
        use std::io::{self, Write as _};
        let mut w = io::Cursor::new(&mut $buf[..]);
        write!(w, $fmt).map(move |_| w.position() as usize)
    }};

    ($buf:ident, $fmt:literal, $($arg:expr),*) => {{
        use std::io::{self, Write as _};
        let mut w = io::Cursor::new(&mut $buf[..]);
        write!(w, $fmt, $($arg),*).map(move |_| w.position() as usize)
    }};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn write_int() {
        let mut buf = [0; 32];

        let n = write_fmt!(buf, "{}", 42).expect("failed to write an int");
        assert_eq!(2, n);

        let s = std::str::from_utf8(&buf[..n]).expect("invalid buffer value");
        assert_eq!("42", s);
    }

    #[test]
    #[should_panic(expected = "failed to write an int")]
    fn buffer_overflow() {
        let mut buf = [0; 1];
        write_fmt!(buf, "{}", 42).expect("failed to write an int");
    }
}
