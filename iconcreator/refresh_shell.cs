// Following C# code is used to refresh the folder icons after the icon has been changed.
// Code is taken from https://stackoverflow.com/a/49818607/13292223
[System.Runtime.InteropServices.DllImport("Shell32.dll")]
private static extern int SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);

public static void Refresh() {
    SHChangeNotify(0x8000000, 0x1000, IntPtr.Zero, IntPtr.Zero);
}